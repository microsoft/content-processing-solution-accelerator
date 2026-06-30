# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Configuration model for Agent Framework service discovery.

Reads Azure OpenAI endpoints, deployment names, and API versions
from environment variables and assembles per-service ``ServiceConfig``
objects used by ``AgentFrameworkHelper`` to create clients.
"""

import os

from pydantic import Field, model_validator

from libs.application.application_configuration import _configuration_base
from libs.application.service_config import ServiceConfig


class AgentFrameworkSettings(_configuration_base):
    """Settings for Agent Framework service discovery and client creation.

    Automatically discovers Azure OpenAI services from environment variables
    using configurable prefixes and validates each service configuration.

    Attributes:
        global_llm_service: Default LLM provider name.
        service_configs: Discovered per-service configuration objects.
        use_entra_id: Whether to use Entra ID token-based auth.
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
        # Store custom service prefixes
        if custom_service_prefixes is None:
            custom_service_prefixes = {}

        # Load environment variables from file if provided
        if env_file_path and os.path.exists(env_file_path):
            self._load_env_file(env_file_path)

        # Set custom service prefixes before calling super().__init__
        kwargs["custom_service_prefixes"] = custom_service_prefixes
        kwargs["use_entra_id"] = use_entra_id
        super().__init__(**kwargs)

    def _load_env_file(self, env_file_path: str):
        """Load environment variables from a .env file"""
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
        """Automatically discover and configure services based on environment variables"""
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
        """Get configuration for a specific service"""
        return self.service_configs.get(service_id)

    def get_available_services(self) -> list[str]:
        """Get list of available service IDs"""
        return list(self.service_configs.keys())

    def has_service(self, service_id: str) -> bool:
        """Check if a service is available"""
        return service_id in self.service_configs

    def refresh_services(self):
        """
        Re-discover and configure all services based on current environment variables
        Useful after adding environment variables or service prefixes
        """
        self.discover_services()
