# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import asyncio
import os
import sys

from helpers.azure_credential_utils import get_azure_credential

from libs.base.application_main import AppMainBase
from libs.process_host import handler_type_loader
from libs.process_host.handler_process_host import HandlerHostManager

# Add the src directory to the PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), "libs"))


class Application(AppMainBase):
    def __init__(self, **data):
        # For Development purpose, load the .env file from the current directory
        # and set the environment variables
        # This is not recommended for production usage
        # Use Azure App Configuration for production usage
        super().__init__(
            env_file_path=os.path.join(os.path.dirname(__file__), ".env.dev"),
            **data,
        )
        self._initialize_application()

    def _initialize_application(self):
        # Add Azure Credential
        self.application_context.set_credential(get_azure_credential())

    async def run(self, test_mode: bool = False):
        # Get Process lists from the configuration - ex. ["extract", "transform", "evaluate", "save", "custom1", "custom2"....]
        steps = self.application_context.configuration.app_process_steps

        # Prepare Process Manager
        handler_host_manager = HandlerHostManager()
        for step in steps:
            # Dynamic Processor Loader
            loaded_handler = handler_type_loader.load(step)(
                appContext=self.application_context,
                step_name=step,
            )

            # Register Process to the Process Manager
            # args => ShowInformation : False on Production
            handler_host_manager.add_handlers_as_process(
                target_function=loaded_handler.connect_queue,
                process_name=loaded_handler.handler_name,
                args=(False, self.application_context, step),
            )

        # Start All registered processes
        await handler_host_manager.start_handler_processes(test_mode)


async def main():
    _app: Application = Application()
    await _app.run()


if __name__ == "__main__":
    asyncio.run(main())
