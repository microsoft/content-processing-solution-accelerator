# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Abstract base for the application bootstrap sequence.

Orchestrates the startup order: load .env → read Azure App Configuration →
populate AppContext with configuration and credentials → configure logging →
call the concrete ``initialize()`` implemented by the subclass.
"""

import inspect
import logging
import os
from abc import ABC, abstractmethod

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from app.libs.application.application_configuration import (
    AppConfiguration,
    EnvConfiguration,
)
from app.libs.application.application_context import AppContext
from app.libs.azure.app_configuration.helper import AppConfigurationHelper


class Application_Base(ABC):
    """Abstract bootstrap base that every concrete application must extend.

    Responsibilities:
        1. Load environment variables from a ``.env`` file.
        2. Pull remote config from Azure App Configuration into the process env.
        3. Build and populate an AppContext with configuration and credentials.
        4. Set up Python logging based on configuration flags.
        5. Invoke the concrete ``initialize()`` hook.

    Attributes:
        application_context: Fully wired DI container available after ``__init__``.
    """

    application_context: AppContext = None

    @abstractmethod
    def run(self):
        """Start the application server (must be implemented by subclasses)."""
        raise NotImplementedError("The run method must be implemented by subclasses.")

    @abstractmethod
    def initialize(self):
        """Wire up middleware, routers, and dependencies (must be implemented)."""
        raise NotImplementedError(
            "The initialize method must be implemented by subclasses."
        )

    def __init__(self, env_file_path: str | None = None, **data):
        """Execute the full bootstrap sequence.

        Steps:
            1. Load ``.env`` from *env_file_path* (or derive from subclass location).
            2. Read Azure App Configuration and inject values into ``os.environ``.
            3. Populate ``application_context`` with config and Azure credentials.
            4. Configure Python logging unconditionally.
            5. Call ``self.initialize()``.

        Args:
            env_file_path: Explicit path to a ``.env`` file (optional).
        """
        super().__init__(**data)

        self._load_env(env_file_path=env_file_path)

        self.application_context = AppContext()
        self.application_context.set_credential(DefaultAzureCredential())

        app_config_endpoint: str | None = EnvConfiguration().app_config_endpoint
        if app_config_endpoint != "" and app_config_endpoint is not None:
            AppConfigurationHelper(
                app_config_endpoint=app_config_endpoint
            ).read_and_set_environmental_variables()

        self.application_context.set_configuration(AppConfiguration())

        # Configure logging unconditionally
        logging_level = getattr(
            logging,
            self.application_context.configuration.app_logging_level,
            logging.INFO,
        )
        logging.basicConfig(
            level=logging_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        # Suppress noisy Azure SDK and OpenTelemetry internal loggers
        logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
        logging.getLogger("azure.core.pipeline.policies._universal").setLevel(logging.WARNING)
        logging.getLogger("opentelemetry.sdk").setLevel(logging.WARNING)
        logging.getLogger("azure.monitor.opentelemetry.exporter.export._base").setLevel(logging.WARNING)

        if self.application_context.configuration.azure_logging_packages:
            azure_level = getattr(
                logging,
                self.application_context.configuration.azure_package_logging_level.upper(),
                logging.WARNING,
            )
            for logger_name in filter(
                None,
                (
                    pkg.strip()
                    for pkg in self.application_context.configuration.azure_logging_packages.split(
                        ","
                    )
                ),
            ):
                logging.getLogger(logger_name).setLevel(azure_level)

        self.initialize()

    def _load_env(self, env_file_path: str | None = None):
        """Load a ``.env`` file, deriving the path from the subclass if not given.

        Args:
            env_file_path: Explicit path; when ``None`` the directory of the
                concrete subclass file is used.

        Returns:
            The resolved path that was loaded.
        """
        if env_file_path:
            load_dotenv(dotenv_path=env_file_path)
            return env_file_path

        derived_class_location = self._get_derived_class_location()
        env_file_path = os.path.join(os.path.dirname(derived_class_location), ".env")
        load_dotenv(dotenv_path=env_file_path)
        return env_file_path

    def _get_derived_class_location(self):
        """Return the filesystem path of the concrete subclass source file."""
        return inspect.getfile(self.__class__)
