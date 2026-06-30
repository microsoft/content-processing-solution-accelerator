# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Per-LLM-service configuration descriptor.

Parses prefixed environment variables (e.g. ``AZURE_OPENAI_*``) into a
typed object consumed by the agent framework when connecting to Azure
OpenAI or other LLM backends.
"""


class ServiceConfig:
    """Holds endpoint, deployment, and auth details for one LLM service.

    Responsibilities:
        1. Extract service-specific env vars using a naming prefix.
        2. Validate that minimum required fields are present.
        3. Serialise to a dict for service-creation APIs.

    Attributes:
        service_id: Unique identifier for this service.
        use_entra_id: Whether Entra ID (AAD) auth is used instead of API key.
        prefix: Environment-variable prefix (e.g. ``AZURE_OPENAI``).
        api_version: API version string.
        chat_deployment_name: Chat completion deployment name.
        text_deployment_name: Text completion deployment name.
        embedding_deployment_name: Embedding deployment name.
        endpoint: Service endpoint URL.
        base_url: Alternative base URL.
        api_key: API key (only when *use_entra_id* is False).
    """

    def __init__(
        self,
        service_id: str,
        prefix: str,
        env_vars: dict[str, str],
        use_entra_id: bool = True,
    ):
        self.service_id = service_id
        self.use_entra_id = use_entra_id
        self.prefix = prefix
        self.api_version = env_vars.get(f"{prefix}_API_VERSION", "")
        self.chat_deployment_name = env_vars.get(f"{prefix}_CHAT_DEPLOYMENT_NAME", "")
        self.text_deployment_name = env_vars.get(f"{prefix}_TEXT_DEPLOYMENT_NAME", "")
        self.embedding_deployment_name = env_vars.get(
            f"{prefix}_EMBEDDING_DEPLOYMENT_NAME", ""
        )

        # Handle different endpoint naming conventions
        self.endpoint = env_vars.get(f"{prefix}_ENDPOINT", "")
        self.base_url = env_vars.get(f"{prefix}_BASE_URL", "")
        self.api_key = env_vars.get(f"{prefix}_API_KEY", "")

    def is_valid(self) -> bool:
        """Return True when endpoint, deployment, and auth are all present."""
        has_auth = True if self.use_entra_id else bool(self.api_key)

        # Always need endpoint and chat deployment name
        has_required = bool(self.endpoint and self.chat_deployment_name)

        return has_auth and has_required

    def to_dict(self) -> dict[str, str | None]:
        """Serialise to a dict suitable for LLM service-creation APIs."""
        return {
            "api_version": self.api_version or None,
            "chat_deployment_name": self.chat_deployment_name or None,
            "text_deployment_name": self.text_deployment_name or None,
            "embedding_deployment_name": self.embedding_deployment_name or None,
            "endpoint": self.endpoint or None,
            "base_url": self.base_url or None,
            "api_key": self.api_key or None,
        }
