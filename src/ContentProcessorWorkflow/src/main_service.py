# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Queue-based claim-processing service entry point.

Bootstraps the application context, registers services, and starts a
long-running queue worker that:
    - Processes claim-processing requests from Azure Storage Queue.
    - Handles concurrent processing with configurable workers.
    - Implements retry logic with exponential backoff.
    - Supports graceful shutdown via SIGINT/SIGTERM.
"""

import asyncio
import logging
import os

from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry.sdk.resources import Resource
from sas.storage.blob.async_helper import AsyncStorageBlobHelper

from utils.telemetry_filter import install_noise_filter

from libs.agent_framework.agent_framework_helper import AgentFrameworkHelper
from libs.agent_framework.mem0_async_memory import Mem0AsyncMemoryManager
from libs.agent_framework.middlewares import (
    DebuggingMiddleware,
    InputObserverMiddleware,
    LoggingFunctionMiddleware,
)
from libs.base.application_base import ApplicationBase
from repositories.claim_processes import Claim_Processes
from services.content_process_service import ContentProcessService
from services.queue_service import (
    ClaimProcessingQueueService,
    QueueServiceConfig,
)
from steps.claim_processor import ClaimProcessor
from utils.credential_util import get_azure_credential
from utils.logging_utils import configure_application_logging

logger = logging.getLogger(__name__)


class ClaimsQueueWorkerService(ApplicationBase):
    """
    Queue-based claim processing service application.

    Transforms the direct-execution claim processing workflow into a scalable service that:
    - Processes claim processing requests from Azure Storage Queue
    - Handles concurrent processing with multiple workers
    - Implements retry logic with exponential backoff
    - Provides comprehensive error handling and monitoring

    Operationally, this class:
    - bootstraps the application context (config + DI container)
    - registers the services required by queue processing
    - builds runtime configuration from environment variables
    - starts/stops the queue worker and (optionally) the control API

    The entrypoint is `run_queue_service()` which constructs this app and runs it
    until stopped (SIGINT/SIGTERM in containers typically surface as KeyboardInterrupt).
    """

    def __init__(self, config_override: dict | None = None, debug_mode: bool = False):
        """Initialize the queue service application.

        Args:
            config_override: Optional configuration values to override environment defaults.
            debug_mode: Enables verbose debug logging and extra diagnostics.

        Runtime notes:
            - Loads environment configuration from the local `.env` next to this file.
            - Calls `initialize()` immediately, so the DI container is ready before
              the service loop begins.
        """
        super().__init__(env_file_path=os.path.join(os.path.dirname(__file__), ".env"))
        self.queue_service: ClaimProcessingQueueService | None = None
        self.config_override = config_override or {}
        self.debug_mode = debug_mode

        # Configure logging based on debug_mode from constructor
        self._configure_logging()
        self._configure_telemetry()
        self.initialize()

    def _configure_logging(self):
        """Configure application logging for the current debug mode.

        This applies the repository's logging policy (including suppression of
        overly noisy third-party logs). When `debug_mode` is enabled, the service
        emits additional debug diagnostics to help trace queue processing.
        """

        # Apply comprehensive verbose logging suppression
        configure_application_logging(debug_mode=self.debug_mode)

        if self.debug_mode:
            logger.debug("Debug logging enabled - level set to DEBUG")
            logger.debug("Verbose third-party logging suppressed to reduce noise")

    def _configure_telemetry(self):
        """Configure Azure Monitor for OpenTelemetry if connection string is set."""
        connection_string = self.application_context.configuration.applicationinsights_connection_string
        if connection_string:
            configure_azure_monitor(
                connection_string=connection_string,
                resource=Resource.create({"service.name": "ContentProcessorWorkflow"}),
                logger_name="utils",
            )
            install_noise_filter(
                noisy_names=frozenset({
                    "QueueClient.receive_messages",
                    "MessagesOperations.dequeue",
                    "GET /msi/token",
                }),
                noisy_suffixes=("/claim-process-queue",),
            )
            logger.info("Application Insights configured for ContentProcessorWorkflow")

    def initialize(self):
        """Bootstrap the application context and register services.

        Populates the DI container with agent-framework helpers, middlewares,
        repository services, and the queue-processing service.
        """
        logger.info("Application initialized.")
        self.register_services()

    def register_services(self):
        """Populate the DI container with all services needed by the queue worker."""
        self.application_context.add_singleton(
            AgentFrameworkHelper, AgentFrameworkHelper()
        )
        self.application_context.get_service(AgentFrameworkHelper).initialize(
            self.application_context.llm_settings
        )

        (
            self.application_context.add_singleton(
                DebuggingMiddleware, DebuggingMiddleware
            )
            .add_singleton(LoggingFunctionMiddleware, LoggingFunctionMiddleware)
            .add_singleton(InputObserverMiddleware, InputObserverMiddleware)
            .add_singleton(Mem0AsyncMemoryManager, Mem0AsyncMemoryManager)
            .add_transient(
                ClaimProcessor,
                lambda: ClaimProcessor(app_context=self.application_context),
            )
            .add_async_singleton(
                AsyncStorageBlobHelper,
                lambda: AsyncStorageBlobHelper(
                    account_name=self.application_context.configuration.app_storage_account_name,
                    credential=get_azure_credential(),
                ),
            )
            .add_singleton(
                Claim_Processes,
                lambda: Claim_Processes(
                    connection_string=self.application_context.configuration.app_cosmos_connstr,
                    database_name=self.application_context.configuration.app_cosmos_database,
                    container_name=self.application_context.configuration.app_cosmos_container_batch_process,
                ),
            )
            .add_singleton(
                ContentProcessService,
                lambda: ContentProcessService(
                    config=self.application_context.configuration,
                    credential=get_azure_credential(),
                ),
            )
        )

        config = self._build_service_config(self.config_override)

        self.queue_service = ClaimProcessingQueueService(
            config=config,
            app_context=self.application_context,
            debug_mode=self.debug_mode,  # Use the debug_mode from constructor
        )

        logger.info("Claim Processing Service initialized for Docker deployment")

    def _build_service_config(
        self, config_override: dict | None = None
    ) -> QueueServiceConfig:
        """Build service configuration from environment variables and overrides.

                Operational behavior:
                        - These settings control visibility timeout, poll cadence, and worker
                            concurrency for queue processing.
                        - The queue connection identifiers are sourced from
                            `self.application_context.configuration`.

                This reads the following environment variables (Docker-friendly) and
                converts them to the appropriate types:

        - `VISIBILITY_TIMEOUT_MINUTES` (default: 5)
        - `POLL_INTERVAL_SECONDS` (default: 5)
        - `MESSAGE_TIMEOUT_MINUTES` (default: 25)
        - `CONCURRENT_WORKERS` (default: 1)

        Any `config_override` values are applied last, so callers can adjust
        behavior for local debugging/testing without changing environment.
        """

        visibility_timeout = os.getenv("VISIBILITY_TIMEOUT_MINUTES", "5")
        poll_interval = os.getenv("POLL_INTERVAL_SECONDS", "5")
        message_timeout = os.getenv("MESSAGE_TIMEOUT_MINUTES", "25")
        concurrent_workers = os.getenv("CONCURRENT_WORKERS", "1")
        queue_name = os.getenv("CLAIM_PROCESS_QUEUE_NAME", "claim-process-queue")
        dead_letter_queue_name = os.getenv(
            "DEAD_LETTER_QUEUE_NAME", "claim-process-dead-letter-queue"
        )
        max_receive_attempts = os.getenv("MAX_RECEIVE_ATTEMPTS", "3")
        retry_visibility_delay_seconds = os.getenv(
            "RETRY_VISIBILITY_DELAY_SECONDS", "5"
        )

        if self.debug_mode:
            logger.debug("Environment variables:")
            logger.debug(
                "  VISIBILITY_TIMEOUT_MINUTES: %s (type: %s)",
                visibility_timeout,
                type(visibility_timeout),
            )
            logger.debug(
                "  POLL_INTERVAL_SECONDS: %s (type: %s)",
                poll_interval,
                type(poll_interval),
            )
            logger.debug(
                "  MESSAGE_TIMEOUT_MINUTES: %s (type: %s)",
                message_timeout,
                type(message_timeout),
            )
            logger.debug(
                "  CONCURRENT_WORKERS: %s (type: %s)",
                concurrent_workers,
                type(concurrent_workers),
            )

        config = QueueServiceConfig(
            use_entra_id=True,
            storage_account_name=self.application_context.configuration.app_storage_account_name,  # type:ignore
            queue_name=queue_name,  # type:ignore
            dead_letter_queue_name=dead_letter_queue_name,
            visibility_timeout_minutes=int(visibility_timeout)
            if isinstance(visibility_timeout, str)
            else visibility_timeout,
            concurrent_workers=int(concurrent_workers)
            if isinstance(concurrent_workers, str)
            else concurrent_workers,
            poll_interval_seconds=int(poll_interval)
            if isinstance(poll_interval, str)
            else poll_interval,
            message_timeout_minutes=int(message_timeout)
            if isinstance(message_timeout, str)
            else message_timeout,
            max_receive_attempts=int(max_receive_attempts)
            if isinstance(max_receive_attempts, str)
            else max_receive_attempts,
            retry_visibility_delay_seconds=int(retry_visibility_delay_seconds)
            if isinstance(retry_visibility_delay_seconds, str)
            else retry_visibility_delay_seconds,
        )

        if config_override:
            for key, value in config_override.items():
                if hasattr(config, key):
                    setattr(config, key, value)

        return config

    async def start_service(self):
        """Start the queue processing service.

        Runtime flow:
            1) Build/start the optional control API (if enabled)
            2) Start the queue worker loop (`QueueMigrationService.start_service()`)

        Lifecycle guarantees:
            - Blocks until the worker stops or an exception escapes.
            - Always attempts a graceful shutdown in `finally`.
        """
        if not self.queue_service:
            raise RuntimeError(
                "Service not initialized. Call initialize_service() first."
            )

        logger.info("Starting Queue-based Claim Processing Service...")

        try:
            # Start the service (this will run until stopped)
            await self.queue_service.start_service()
        except KeyboardInterrupt:
            logger.info("Service interrupted by user (SIGTERM/SIGINT)")
        except Exception as e:
            logger.error(f"Service error: {e}")
        finally:
            await self.shutdown_service()
            logger.info("Service stopped")

    async def shutdown_service(self):
        """Gracefully shut down the service and release resources.

        Runtime order:
            - Stop the queue worker
        """
        if self.queue_service:
            logger.info("Shutting down Claim Processing Service...")
            await self.queue_service.stop_service()
            self.queue_service = None

        logger.info("Service shutdown complete")

    async def force_stop_service(self):
        """Force immediate shutdown of the service.

        This bypasses the normal graceful stop behavior. Use when the worker loop
        is stuck or needs immediate termination.
        """
        if self.queue_service:
            logger.warning("Force stopping Claim Processing Service...")
            await self.queue_service.force_stop()
            self.queue_service = None

        logger.info("Service force stopped")

    def is_service_running(self) -> bool:
        """Return whether the queue worker service is currently running."""
        return self.queue_service is not None and self.queue_service.is_running

    def get_service_status(self) -> dict:
        """Get current service status for reporting and health checks.

        Returns a merged view of the underlying queue service status plus a
        `docker_health` field to support container health probes.
        """
        if not self.queue_service:
            return {
                "status": "not_initialized",
                "running": False,
                "docker_health": "unhealthy",
                "timestamp": asyncio.get_event_loop().time()
                if hasattr(asyncio, "get_event_loop")
                else None,
            }

        status = self.queue_service.get_service_status()
        status["running"] = self.is_service_running()
        status["docker_health"] = (
            "healthy" if self.is_service_running() else "unhealthy"
        )
        return status

    async def run(self):
        """Run the claim processing service until stopped."""
        await self.start_service()


async def run_queue_service(
    config_override: dict | None = None, debug_mode: bool = False
):
    """Run the queue-based claim-processing service.

    Constructs a ``ClaimsQueueWorkerService``, wires the DI container, and
    starts the queue worker loop.  Blocks until stopped (SIGINT/SIGTERM).

    On ``KeyboardInterrupt`` the service shuts down gracefully and exits
    cleanly.  On other exceptions, cleanup is attempted before the error is
    re-raised so Docker restart policies can take effect.
    """
    app = ClaimsQueueWorkerService(
        config_override=config_override,
        debug_mode=debug_mode,
    )

    try:
        logger.info("Starting queue service...")
        await app.run()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        try:
            if app.queue_service:
                await app.queue_service.stop_service()
            logger.info("Service shutdown complete")
        except Exception as cleanup_error:
            logger.warning(f"Error during cleanup: {cleanup_error}")
        logger.info("Service stopped")
    except Exception as e:
        logger.error(f"Failed to run queue service: {e}")
        try:
            if app.queue_service:
                await app.queue_service.stop_service()
        except Exception as cleanup_error:
            logger.debug(
                "Ignoring cleanup error while re-raising original failure: %s",
                cleanup_error,
            )
        raise


if __name__ == "__main__":
    debug_mode = False
    asyncio.run(run_queue_service(debug_mode=debug_mode))
