# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Content Processor application entry point.

Bootstraps the Application instance, wires up Azure credentials, agent
framework, and content-understanding services, then dynamically loads
pipeline step handlers and starts them as concurrent queue consumers.
"""

import asyncio
import logging
import os
import sys

from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry.sdk.resources import Resource

from libs.agent_framework.agent_framework_helper import AgentFrameworkHelper
from libs.azure_helper.content_understanding import AzureContentUnderstandingHelper
from libs.base.application_main import AppMainBase
from libs.process_host import handler_type_loader
from libs.process_host.handler_process_host import HandlerHostManager
from libs.utils.azure_credential_utils import get_azure_credential

logger = logging.getLogger(__name__)

sys.path.append(os.path.join(os.path.dirname(__file__), "libs"))


class Application(AppMainBase):
    """Top-level application that orchestrates the content-processing pipeline.

    Responsibilities:
        1. Initialize Azure credentials and shared services.
        2. Dynamically load pipeline step handlers from configuration.
        3. Start all handlers as concurrent queue-consuming processes.

    Attributes:
        application_context: Shared context carrying configuration, credentials,
            and registered service singletons.
    """

    def __init__(self, **data):
        super().__init__(
            env_file_path=os.path.join(os.path.dirname(__file__), ".env"),
            **data,
        )
        self._initialize_application()

    def _initialize_application(self):
        """Wire up Azure credentials, telemetry, and register shared services.

        Steps:
            1. Configure Azure Monitor telemetry if connection string is available.
            2. Set Azure credential on the application context.
            3. Register AgentFrameworkHelper and initialize it with LLM settings.
            4. Register an async factory for AzureContentUnderstandingHelper.
        """
        self._configure_telemetry()
        self.application_context.set_credential(get_azure_credential())

        self.application_context.add_singleton(
            AgentFrameworkHelper, AgentFrameworkHelper()
        )
        self.application_context.get_service(AgentFrameworkHelper).initialize(
            self.application_context.llm_settings
        )

        self.application_context.add_async_singleton(
            AzureContentUnderstandingHelper,
            lambda: AzureContentUnderstandingHelper(
                self.application_context.configuration.app_content_understanding_endpoint
            ),
        )

    def _configure_telemetry(self):
        """Configure Azure Monitor for OpenTelemetry if connection string is set."""
        connection_string = self.application_context.configuration.applicationinsights_connection_string
        if connection_string:
            configure_azure_monitor(
                connection_string=connection_string,
                resource=Resource.create({"service.name": "ContentProcessor"}),
                logger_name="libs",
            )
            logger.info("Application Insights configured for ContentProcessor")
        else:
            logger.warning(
                "No Application Insights connection string found. Telemetry disabled."
            )

    async def run(self, test_mode: bool = False):
        """Load pipeline step handlers and start them as concurrent processes.

        Args:
            test_mode: When True, handlers run a single iteration then exit.
        """
        steps = self.application_context.configuration.app_process_steps

        handler_host_manager = HandlerHostManager()
        for step in steps:
            loaded_handler = handler_type_loader.load(step)(
                appContext=self.application_context,
                step_name=step,
            )

            handler_host_manager.add_handlers_as_process(
                target_function=loaded_handler.connect_queue,
                process_name=loaded_handler.handler_name,
                args=(False, self.application_context, step),
            )

        await handler_host_manager.start_handler_processes(test_mode)


async def main():
    """Create and run the Application."""
    _app: Application = Application()
    await _app.run()


if __name__ == "__main__":
    asyncio.run(main())
