# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Pydantic settings model for Agent Framework service discovery.

This module defines ``AgentFrameworkSettings``, which auto-discovers Azure OpenAI
service endpoints from environment variables at construction time.  The discovery
uses configurable *prefix conventions* so that a single settings object can manage
multiple independent OpenAI deployments (e.g. ``default``, ``fast``, ``reasoning``).

Discovery algorithm (executed as a Pydantic ``model_validator``):
    1. Start with the built-in ``default`` prefix ``AZURE_OPENAI``.
    2. Merge any ``custom_service_prefixes`` passed at construction.
    3. For each prefix, read ``{PREFIX}_ENDPOINT``, ``{PREFIX}_CHAT_DEPLOYMENT_NAME``,
       and ``{PREFIX}_API_VERSION`` from the environment.
    4. If the required fields are present, register a ``ServiceConfig`` under the
       corresponding ``service_id``.

Optional .env file support:
    Pass ``env_file_path`` to the constructor to pre-load a ``.env`` file into
    ``os.environ`` before discovery runs.  Existing environment variables are
    **not** overwritten.

Example:
    .. code-block:: python

        settings = AgentFrameworkSettings(
            custom_service_prefixes={"fast": "AZURE_OPENAI_FAST"},
            env_file_path=".env",
        )
        cfg = settings.get_service_config("fast")
        print(cfg.endpoint, cfg.chat_deployment_name)
"""

import os

from pydantic import Field, model_validator

from libs.application.application_configuration import _configuration_base
from libs.application.service_config import ServiceConfig


class AgentFrameworkSettings(_configuration_base):
    """Pydantic settings that auto-discover Azure OpenAI services from env vars.

    Inherits from ``_configuration_base`` to gain standard config loading behavior.
    On construction, the ``discover_services`` model validator scans the environment
    for service-prefixed variables and populates ``service_configs``.

    Attributes:
        global_llm_service: Global LLM provider label (default ``"AzureOpenAI"``).
        azure_tracing_enabled: Whether Azure Monitor tracing is turned on.
        azure_ai_agent_project_connection_string: Connection string for Azure AI
            Agent projects (optional).
        azure_ai_agent_model_deployment_name: Default model deployment for
            Azure AI Agent (optional).
        service_configs: Discovered ``ServiceConfig`` instances keyed by service ID
            (populated automatically, excluded from serialization).
        custom_service_prefixes: Mapping of service ID → env-var prefix for
            non-default services.
        use_entra_id: Whether to authenticate via Entra ID (default ``True``).
    """

    global_llm_service: str | None = "AzureOpenAI"
    azure_tracing_enabled: bool = Field(default=False, alias="AZURE_TRACING_ENABLED")
    azure_ai_agent_project_connection_string: str = Field(
        default="", alias="AZURE_AI_AGENT_PROJECT_CONNECTION_STRING"
    )
    azure_ai_agent_model_deployment_name: str = Field(
        default="", alias="AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME"
    )

    # Dynamic service configurations will be populated in model_validator
    service_configs: dict[str, ServiceConfig] = Field(
        default_factory=dict, exclude=True
    )
    # Store custom service prefixes - use PrivateAttr for private fields
    custom_service_prefixes: dict[str, str] = Field(default_factory=dict, exclude=True)

    # Entra ID Enabled
    use_entra_id: bool = Field(default=True)

    def __init__(
        self,
        use_entra_id: bool = True,
        env_file_path: str | None = None,
        custom_service_prefixes: dict[str, str] | None = None,
        **kwargs,
    ):
        """Initialize settings with optional .env file and custom prefixes.

        Processing steps:
            1. Normalize ``custom_service_prefixes`` to an empty dict if not given.
            2. If ``env_file_path`` points to an existing file, load it into
               ``os.environ`` (existing vars are preserved).
            3. Delegate to ``_configuration_base.__init__`` which triggers the
               ``discover_services`` model validator.

        Args:
            use_entra_id: If ``True``, use Entra ID token providers instead
                of API keys.
            env_file_path: Optional path to a ``.env`` file to pre-load.
            custom_service_prefixes: Extra ``{service_id: ENV_PREFIX}`` entries
                to discover alongside the built-in ``default`` prefix.
            **kwargs: Forwarded to ``_configuration_base``.
        """
        if custom_service_prefixes is None:
            custom_service_prefixes = {}

        # Load environment variables from file if provided
        if env_file_path and os.path.exists(env_file_path):
            self._load_env_file(env_file_path)

        # Set custom service prefixes before calling super().__init__
        kwargs["custom_service_prefixes"] = custom_service_prefixes
        kwargs["use_entra_id"] = use_entra_id
        super().__init__(**kwargs)

    def _load_env_file(self, env_file_path: str) -> None:
        """Load a .env file into ``os.environ`` without overwriting existing vars.

        Processing steps:
            1. Open the file with UTF-8 encoding.
            2. Skip blank lines and comments (``#`` prefix).
            3. Split on the first ``=`` to extract key/value.
            4. Strip surrounding quotes from the value.
            5. Only set the variable if it is absent or empty in the environment.

        Args:
            env_file_path: Absolute or relative path to the ``.env`` file.

        Raises:
            ValueError: If the file is not found or cannot be parsed.
        """
        try:
            with open(env_file_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        value = value.strip().strip('"').strip("'")
                        if key not in os.environ or not os.environ[key]:
                            os.environ[key] = value
        except FileNotFoundError:
            raise ValueError(f"Environment file not found: {env_file_path}")
        except Exception as e:
            raise ValueError(f"Error loading environment file: {e}")

    @model_validator(mode="after")
    def discover_services(self):
        """Auto-discover service configurations from environment variables.

        Runs as a Pydantic ``model_validator(mode='after')`` so it executes
        immediately after field assignment.

        Processing steps:
            1. Build a prefix map starting with ``{"default": "AZURE_OPENAI"}``.
            2. Merge ``custom_service_prefixes``.
            3. For each entry, construct a ``ServiceConfig`` from env vars
               matching the prefix (``{PREFIX}_ENDPOINT``, etc.).
            4. Validate the config; log warnings for incomplete entries.
            5. Store valid configs in ``self.service_configs``.

        Returns:
            ``self`` (required by Pydantic model validators).
        """
        env_vars = dict(os.environ)

        # Start with default service prefix (always available)
        service_prefixes = {
            "default": "AZURE_OPENAI",  # Default service uses AZURE_OPENAI_ prefix
        }

        # Add custom service prefixes
        service_prefixes.update(self.custom_service_prefixes)

        discovered_configs = {}

        for service_id, prefix in service_prefixes.items():
            config = ServiceConfig(service_id, prefix, env_vars, use_entra_id=True)
            if config.is_valid():
                discovered_configs[service_id] = config
                print(
                    f"Discovered valid service configuration: {service_id} (prefix: {prefix})"
                )
            else:
                missing_fields = []
                if (not self.use_entra_id) and (not config.api_key):
                    missing_fields.append("API_KEY")
                if not config.endpoint:
                    missing_fields.append("ENDPOINT")
                if not config.chat_deployment_name:
                    missing_fields.append("CHAT_DEPLOYMENT_NAME")
                print(
                    f"Incomplete service configuration for {service_id} (prefix: {prefix}) - Missing: {', '.join(missing_fields)}"
                )

        self.service_configs = discovered_configs
        return self

    def get_service_config(self, service_id: str) -> ServiceConfig | None:
        """Retrieve the ``ServiceConfig`` for a given service ID.

        Args:
            service_id: Identifier registered during discovery (e.g. ``"default"``).

        Returns:
            The matching ``ServiceConfig``, or ``None`` if the service was not
            discovered or its configuration was incomplete.
        """
        return self.service_configs.get(service_id)

    def get_available_services(self) -> list[str]:
        """Return the IDs of all successfully discovered services.

        Returns:
            List of service ID strings (e.g. ``["default", "fast"]``).
        """
        return list(self.service_configs.keys())

    def has_service(self, service_id: str) -> bool:
        """Check whether a service ID was successfully discovered.

        Args:
            service_id: Identifier to check.

        Returns:
            ``True`` if the service has a valid ``ServiceConfig``.
        """
        return service_id in self.service_configs

    def refresh_services(self) -> None:
        """Re-run service discovery against the current environment.

        Useful after programmatically setting new environment variables or
        adding entries to ``custom_service_prefixes`` at runtime.
        """
        self.discover_services()
