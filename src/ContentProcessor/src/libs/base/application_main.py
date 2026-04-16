# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Abstract base class that bootstraps configuration, logging, and DI.

Concrete applications (e.g. ``main.Application``) inherit from
``AppMainBase`` and implement ``run()`` to start the pipeline.
"""

import inspect
import logging
import os
from abc import ABC, abstractmethod

from dotenv import load_dotenv

from libs.agent_framework.agent_framework_settings import AgentFrameworkSettings
from libs.application.application_configuration import AppConfiguration
from libs.application.application_context import AppContext
from libs.application.env_config import EnvConfiguration
from libs.azure_helper.app_configuration import AppConfigurationHelper
from libs.base.application_models import AppModelBase


class AppMainBase(ABC, AppModelBase):
    """Abstract application bootstrap that loads config, sets up DI, and configures logging.

    Responsibilities:
        1. Load ``.env`` and Azure App Configuration settings.
        2. Create and populate an ``AppContext`` (DI container).
        3. Configure logging and LLM service settings.

    Attributes:
        application_context: The fully wired DI container.
    """

    application_context: AppContext = None

    @abstractmethod
    def run(self):
        """Start the application (must be implemented by subclasses)."""
        raise NotImplementedError("Method run not implemented")

    def __init__(self, env_file_path: str | None = None, **data):
        super().__init__(**data)

        self._load_env(env_file_path=env_file_path)

        AppConfigurationHelper(
            EnvConfiguration().app_config_endpoint
        ).read_and_set_environmental_variables()

        self.application_context = AppContext()
        self.application_context.set_configuration(AppConfiguration())

        logging_level = getattr(
            logging,
            self.application_context.configuration.app_logging_level,
            logging.INFO,
        )
        logging.basicConfig(level=logging_level)

        self.application_context.llm_settings = AgentFrameworkSettings(
            use_entra_id=True
        )

    def _load_env(self, env_file_path: str | None = None):
        """Load environment variables from a ``.env`` file.

        If *env_file_path* is not provided, derives the path from the
        concrete subclass's file location.

        Args:
            env_file_path: Explicit path to a ``.env`` file.

        Returns:
            The resolved ``.env`` file path.
        """
        if env_file_path:
            load_dotenv(dotenv_path=env_file_path)
            return env_file_path

        derived_class_location = self._get_derived_class_location()
        env_file_path = os.path.join(os.path.dirname(derived_class_location), ".env")
        load_dotenv(dotenv_path=env_file_path)
        return env_file_path

    def _get_derived_class_location(self):
        """Return the file path of the concrete subclass."""
        return inspect.getfile(self.__class__)
