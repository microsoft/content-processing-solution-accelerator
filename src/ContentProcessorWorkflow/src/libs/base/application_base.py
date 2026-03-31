# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Abstract base class that bootstraps every Content Processing service.

``ApplicationBase`` encapsulates the entire startup sequence so that
concrete services only need to implement ``initialize`` and ``run``.
The constructor performs the following steps in order:

    1. Load ``.env`` (either from an explicit path or from the directory
       of the derived class).
    2. Create an ``AppContext`` with ``DefaultAzureCredential``.
    3. If an Azure App Configuration endpoint is found, pull all
       key-value pairs into ``os.environ``.
    4. Build the typed ``Configuration`` object (Pydantic merges env
       vars, ``.env``, and App Config values automatically).
    5. Configure Python ``logging`` when ``app_logging_enable`` is set.
    6. Initialise ``AgentFrameworkSettings`` for LLM service access.

Subclass contract::

    class MyService(ApplicationBase):
        def initialize(self):
            # register DI services, open connections, etc.
            ...

        def run(self):
            # start the main event loop / queue listener
            ...
"""

import inspect
import logging
import os
from abc import ABC, abstractmethod

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from libs.agent_framework.agent_framework_settings import AgentFrameworkSettings
from libs.application.application_configuration import (
    Configuration,
    _envConfiguration,
)
from libs.application.application_context import AppContext
from libs.azure.app_configuration import AppConfigurationHelper


class ApplicationBase(ABC):
    """
    Abstract base that owns the bootstrap lifecycle for every service.

    Subclasses must implement two methods:

    ``initialize``
        Called after the constructor has finished wiring up
        configuration, credentials, and LLM settings.  Use it to
        register DI services, open persistent connections, etc.

    ``run``
        Starts the main processing loop (queue listener, HTTP server,
        scheduled job, etc.).

    Attributes:
        application_context (AppContext):
            Fully configured dependency-injection container populated
            during ``__init__``.  Holds ``configuration``,
            ``credential``, ``llm_settings``, and all registered
            services.
    """

    application_context: AppContext = None

    @abstractmethod
    def run(self):
        """Start the service's main processing loop."""
        raise NotImplementedError("The run method must be implemented by subclasses.")

    @abstractmethod
    def initialize(self):
        """Wire up DI services and any one-time resources."""
        raise NotImplementedError(
            "The initialize method must be implemented by subclasses."
        )

    def __init__(self, env_file_path: str | None = None, **data):
        """
        Execute the full bootstrap sequence.

        Steps:
            1. Load ``.env`` via ``_load_env`` (explicit path or auto-
               discovered next to the derived class file).
            2. Create an ``AppContext`` and attach a
               ``DefaultAzureCredential``.
            3. Read ``APP_CONFIG_ENDPOINT`` from the environment.  If
               present, connect to Azure App Configuration and inject
               all settings into ``os.environ``.
            4. Build the typed ``Configuration`` (Pydantic picks up the
               enriched environment automatically).
            5. If ``app_logging_enable`` is ``True``, configure Python
               ``logging`` at the level specified by
               ``app_logging_level``.
            6. Initialise ``AgentFrameworkSettings`` with Entra ID auth
               and any custom service prefixes.

        Args:
            env_file_path:
                Optional absolute path to a ``.env`` file.  When
                ``None``, the file is looked up in the same directory
                as the concrete subclass source file.
            **data:
                Forwarded to ``super().__init__`` for any mixin or
                Pydantic-model base classes.
        """
        super().__init__(**data)

        self._load_env(env_file_path=env_file_path)

        self.application_context = AppContext()
        self.application_context.set_credential(DefaultAzureCredential())

        app_config_url: str | None = _envConfiguration().app_config_endpoint
        if app_config_url != "" and app_config_url is not None:
            AppConfigurationHelper(
                app_configuration_url=app_config_url,
                credential=self.application_context.credential,
            ).read_and_set_environmental_variables()

        self.application_context.set_configuration(Configuration())

        if self.application_context.configuration.app_logging_enable:
            logging_level = getattr(
                logging, self.application_context.configuration.app_logging_level
            )
            logging.basicConfig(level=logging_level)

        self.application_context.llm_settings = AgentFrameworkSettings(
            use_entra_id=True, custom_service_prefixes={"PHI4": "PHI4"}
        )

    def _load_env(self, env_file_path: str | None = None):
        """
        Locate and load a ``.env`` file into the process environment.

        Resolution order:
            1. If *env_file_path* is provided, use it directly.
            2. Otherwise, derive the path by finding the source file of
               the concrete subclass (via ``inspect.getfile``) and
               looking for ``.env`` in the same directory.

        After ``load_dotenv`` runs, any variables defined in the file
        are available in ``os.environ`` and will be picked up by the
        Pydantic ``BaseSettings``-based ``Configuration`` class.

        Args:
            env_file_path: Optional explicit path to the ``.env`` file.

        Returns:
            str: The resolved path that was loaded.
        """
        if env_file_path:
            load_dotenv(dotenv_path=env_file_path)
            return env_file_path

        derived_class_location = self._get_derived_class_location()
        env_file_path = os.path.join(os.path.dirname(derived_class_location), ".env")
        load_dotenv(dotenv_path=env_file_path)
        return env_file_path

    def _get_derived_class_location(self):
        """
        Return the filesystem path of the concrete subclass source file.

        Uses ``inspect.getfile`` on ``self.__class__`` so that the
        ``.env`` lookup is always relative to the *subclass*, not to
        this base module.

        Returns:
            str: Absolute path to the ``.py`` file of the derived class.
        """
        return inspect.getfile(self.__class__)
