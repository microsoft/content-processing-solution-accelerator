# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Normalised descriptor for a single Azure OpenAI (or compatible) LLM deployment.

Each ``ServiceConfig`` instance collects the scattered environment variables
that define one AI model endpoint — API version, deployment names for chat /
text / embedding, authentication mode — and presents them through a validated,
dictionary-serialisable interface.

Environment variable convention::

    {PREFIX}_API_VERSION
    {PREFIX}_CHAT_DEPLOYMENT_NAME
    {PREFIX}_TEXT_DEPLOYMENT_NAME
    {PREFIX}_EMBEDDING_DEPLOYMENT_NAME
    {PREFIX}_ENDPOINT
    {PREFIX}_BASE_URL          (alternative to ENDPOINT)
    {PREFIX}_API_KEY           (only when Entra ID auth is disabled)

Usage::

    env = dict(os.environ)
    cfg = ServiceConfig("primary", "AZURE_OPENAI", env, use_entra_id=True)
    if cfg.is_valid():
        kernel.add_service(**cfg.to_dict())
"""


class ServiceConfig:
    """
    Validated configuration for a single LLM service deployment.

    Reads a known set of ``{PREFIX}_*`` environment variables from a
    caller-supplied dictionary, stores them as typed attributes, and
    exposes helpers for validation (``is_valid``) and serialisation
    (``to_dict``).

    Authentication modes:
        * **Entra ID** (``use_entra_id=True``, default) — no API key is
          required; the runtime uses ``DefaultAzureCredential``.
        * **API key** (``use_entra_id=False``) — the ``{PREFIX}_API_KEY``
          variable must be set.

    Attributes:
        service_id (str):
            Unique identifier used when registering this service with the
            Semantic Kernel or other orchestrator.
        prefix (str):
            Environment-variable prefix (e.g. ``"AZURE_OPENAI"``).
        use_entra_id (bool):
            ``True`` to rely on managed-identity / Entra ID auth;
            ``False`` to require an explicit API key.
        api_version (str):
            Azure OpenAI API version string (e.g. ``"2024-02-15-preview"``).
        chat_deployment_name (str):
            Deployment name for chat-completion calls.
        text_deployment_name (str):
            Deployment name for text-completion calls.
        embedding_deployment_name (str):
            Deployment name for embedding calls.
        endpoint (str):
            Azure OpenAI resource endpoint URL.
        base_url (str):
            Alternative base URL (some SDKs prefer this over ``endpoint``).
        api_key (str):
            API key string, used only when ``use_entra_id`` is ``False``.
    """

    def __init__(
        self,
        service_id: str,
        prefix: str,
        env_vars: dict[str, str],
        use_entra_id: bool = True,
    ):
        """
        Build a service configuration by extracting ``{prefix}_*`` keys.

        Processing steps:
            1. Store identity fields (``service_id``, ``prefix``, ``use_entra_id``).
            2. Look up each known suffix (``_API_VERSION``, ``_CHAT_DEPLOYMENT_NAME``,
               etc.) in *env_vars*, defaulting to ``""`` when absent.
            3. Resolve the endpoint — ``{PREFIX}_ENDPOINT`` is preferred, with
               ``{PREFIX}_BASE_URL`` as a fallback for SDKs that use that naming.

        Args:
            service_id: Unique identifier for this service registration.
            prefix:     Environment-variable prefix (e.g. ``"AZURE_OPENAI"``).
            env_vars:   Dictionary of environment variables (usually ``os.environ``).
            use_entra_id:
                When ``True`` (default), authentication uses Entra ID /
                ``DefaultAzureCredential`` and ``{PREFIX}_API_KEY`` is ignored.
        """
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
        """
        Return ``True`` when the minimum required settings are present.

        Validation rules:
            * **Endpoint** and **chat deployment name** are always required.
            * **API key** is required only when ``use_entra_id`` is ``False``.

        Returns:
            bool: ``True`` if the service is deployable, ``False`` otherwise.
        """
        # For Entra ID authentication, we don't need api_key
        # For API key authentication, we need api_key
        has_auth = True if self.use_entra_id else bool(self.api_key)

        # Always need endpoint and chat deployment name
        has_required = bool(self.endpoint and self.chat_deployment_name)

        return has_auth and has_required

    def to_dict(self) -> dict[str, str | None]:
        """
        Serialise the configuration to a flat dictionary.

        Empty strings are normalised to ``None`` so callers can pass the
        result directly to SDK constructors that distinguish *missing* from
        *blank* values (e.g. ``kernel.add_service(**cfg.to_dict())``).

        Returns:
            dict[str, str | None]:
                Keys: ``api_version``, ``chat_deployment_name``,
                ``text_deployment_name``, ``embedding_deployment_name``,
                ``endpoint``, ``base_url``, ``api_key``.
        """
        return {
            "api_version": self.api_version or None,
            "chat_deployment_name": self.chat_deployment_name or None,
            "text_deployment_name": self.text_deployment_name or None,
            "embedding_deployment_name": self.embedding_deployment_name or None,
            "endpoint": self.endpoint or None,
            "base_url": self.base_url or None,
            "api_key": self.api_key or None,
        }
