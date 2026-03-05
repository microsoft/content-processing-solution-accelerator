# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Local-development entry point for the claim-processing workflow.

Bootstraps the application context, registers all required services, and
runs a single claim-processing workflow against a hard-coded claim ID.
For production queue-based execution see :mod:`main_service`.
"""

import asyncio
import os

from sas.storage.blob.async_helper import AsyncStorageBlobHelper

from libs.agent_framework.agent_framework_helper import AgentFrameworkHelper
from libs.agent_framework.mem0_async_memory import Mem0AsyncMemoryManager
from libs.agent_framework.middlewares import (
    DebuggingMiddleware,
    InputObserverMiddleware,
    LoggingFunctionMiddleware,
)
from libs.base.application_base import ApplicationBase
from repositories.claim_processes import Claim_Processes
from steps.claim_processor import ClaimProcessor


class Application(ApplicationBase):
    """Local-development application that runs a single claim workflow.

    Responsibilities:
        1. Load configuration from a local ``.env`` file.
        2. Register agent-framework helpers, middlewares, and repository
           services into the DI container.
        3. Execute one claim-processing workflow run for manual testing.
    """

    def __init__(self):
        super().__init__(env_file_path=os.path.join(os.path.dirname(__file__), ".env"))

    def initialize(self):
        """Bootstrap the application context and register services."""
        print(
            "Application initialized with configuration:",
            self.application_context.configuration,
        )

        self.register_services()

    def register_services(self):
        """Populate the DI container with all services needed by the workflow."""
        self.application_context.add_singleton(
            AgentFrameworkHelper, AgentFrameworkHelper()
        )
        self.application_context.get_service(AgentFrameworkHelper).initialize(
            self.application_context.llm_settings
        )

        (
            self.application_context
            .add_singleton(DebuggingMiddleware, DebuggingMiddleware)
            .add_singleton(LoggingFunctionMiddleware, LoggingFunctionMiddleware)
            .add_singleton(InputObserverMiddleware, InputObserverMiddleware)
            .add_singleton(Mem0AsyncMemoryManager, Mem0AsyncMemoryManager)
            .add_transient(
                ClaimProcessor,
                lambda: ClaimProcessor(app_context=self.application_context),
            )
            .add_async_scoped(
                AsyncStorageBlobHelper,
                lambda: AsyncStorageBlobHelper(
                    account_name=self.application_context.configuration.app_storage_account_name,
                    credential=self.application_context.credential,
                ),
            )
            .add_async_scoped(
                Claim_Processes,
                lambda: Claim_Processes(
                    connection_string=self.application_context.configuration.app_cosmos_connstr,
                    database_name=self.application_context.configuration.app_cosmos_database,
                    container_name=self.application_context.configuration.app_cosmos_container_batch_process,
                ),
            )
        )

    async def run(self):
        """Execute a single claim-processing workflow for local testing."""
        claim_processor = self.application_context.get_service(ClaimProcessor)
        input_data = "cbe699df-9cc2-440f-adb5-17ab55154d92"
        process_output = await claim_processor.run(input_data=input_data)

        print(f"Claim Processing Workflow completed. Final Output: {process_output}")


async def main():
    """Create and run the local-development application."""
    app = Application()
    app.initialize()
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
