# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Agent Framework client factory and initialization helpers.

This module centralizes the construction of Agent Framework client instances
used by the migration processor. It provides:
    - A small enum describing supported client types.
    - A helper that initializes clients from `AgentFrameworkSettings` and
      exposes a consistent lookup API.

Operational notes:
    - Authentication is typically provided via Entra ID token providers.
    - Client initialization is driven by configured services in settings.
"""

import logging
from enum import Enum
from typing import TYPE_CHECKING, Any, overload

from utils.credential_util import get_bearer_token_provider

from .agent_framework_settings import AgentFrameworkSettings
from .azure_openai_response_retry import (
    AzureOpenAIChatClientWithRetry,
    AzureOpenAIResponseClientWithRetry,
    RateLimitRetryConfig,
)

if TYPE_CHECKING:
    from agent_framework.azure import (
        AzureAIAgentClient,
        AzureOpenAIAssistantsClient,
        AzureOpenAIChatClient,
        AzureOpenAIResponsesClient,
    )


class ClientType(Enum):
    """Supported Agent Framework client types."""

    OpenAIChatCompletion = "OpenAIChatCompletion"
    OpenAIAssistant = "OpenAIAssistant"
    OpenAIResponse = "OpenAIResponse"
    AzureOpenAIChatCompletion = "AzureOpenAIChatCompletion"
    AzureOpenAIChatCompletionWithRetry = "AzureOpenAIChatCompletionWithRetry"
    AzureOpenAIAssistant = "AzureOpenAIAssistant"
    AzureOpenAIResponse = "AzureOpenAIResponse"
    AzureOpenAIResponseWithRetry = "AzureOpenAIResponseWithRetry"
    AzureOpenAIAgent = "AzureAIAgent"


class AgentFrameworkHelper:
    """Initialize and cache Agent Framework clients for configured services."""

    def __init__(self):
        """Create an empty client registry.

        Call `initialize()` to populate clients from settings.
        """
        self.ai_clients: dict[
            str,
            Any,
        ] = {}

    def initialize(self, settings: AgentFrameworkSettings):
        """Initialize all clients configured in `settings`.

        Args:
            settings: Configuration object describing available services and
                their endpoints/deployments.

        Raises:
            ValueError: If `settings` is not provided.
        """
        if settings is None:
            raise ValueError(
                "AgentFrameworkSettings must be provided to initialize clients."
            )

        self._initialize_all_clients(settings=settings)

    def _initialize_all_clients(self, settings: AgentFrameworkSettings):
        """Create all configured clients and cache them by service ID."""
        if settings is None:
            raise ValueError(
                "AgentFrameworkSettings must be provided to initialize clients."
            )

        self.settings = settings

        for service_id in settings.get_available_services():
            service_config = settings.get_service_config(service_id)
            if service_config is None:
                logging.warning(f"No configuration found for service ID: {service_id}")
                continue

            self.ai_clients[service_id] = AgentFrameworkHelper.create_client(
                client_type=ClientType.AzureOpenAIChatCompletionWithRetry,
                endpoint=service_config.endpoint,
                deployment_name=service_config.chat_deployment_name,
                api_version=service_config.api_version,
                ad_token_provider=get_bearer_token_provider(),
            )

        # Add ChatCompletion Connection
        self.ai_clients["default_chat_completion"] = AgentFrameworkHelper.create_client(
            client_type=ClientType.AzureOpenAIChatCompletionWithRetry,
            endpoint=self.settings.get_service_config("default").endpoint,
            deployment_name=self.settings.get_service_config(
                "default"
            ).chat_deployment_name,
            api_version=self.settings.get_service_config("default").api_version,
            ad_token_provider=get_bearer_token_provider(),
        )

    async def get_client_async(self, service_id: str = "default") -> Any | None:
        """Return a cached client for `service_id`.

        This is declared async to match call sites that may already be async.
        The lookup itself is in-memory.
        """
        return self.ai_clients.get(service_id)

    # Type-specific overloads for better IntelliSense (Type Hint)
    @overload
    @staticmethod
    def create_client(  # noqa: E704
        client_type: type[ClientType.AzureOpenAIChatCompletion],
        *,
        api_key: str | None = None,
        deployment_name: str | None = None,
        endpoint: str | None = None,
        base_url: str | None = None,
        api_version: str | None = None,
        ad_token: str | None = None,
        ad_token_provider: object | None = None,
        token_endpoint: str | None = None,
        credential: object | None = None,
        default_headers: dict[str, str] | None = None,
        async_client: object | None = None,
        env_file_path: str | None = None,
        env_file_encoding: str | None = None,
        instruction_role: str | None = None,
    ) -> "AzureOpenAIChatClient": ...

    @overload
    @staticmethod
    def create_client(  # noqa: E704
        client_type: type[ClientType.AzureOpenAIChatCompletionWithRetry],
        *,
        api_key: str | None = None,
        deployment_name: str | None = None,
        endpoint: str | None = None,
        base_url: str | None = None,
        api_version: str | None = None,
        ad_token: str | None = None,
        ad_token_provider: object | None = None,
        token_endpoint: str | None = None,
        credential: object | None = None,
        default_headers: dict[str, str] | None = None,
        async_client: object | None = None,
        env_file_path: str | None = None,
        env_file_encoding: str | None = None,
        instruction_role: str | None = None,
        retry_config: RateLimitRetryConfig | None = None,
    ) -> AzureOpenAIChatClientWithRetry: ...

    @overload
    @staticmethod
    def create_client(  # noqa: E704
        client_type: type[ClientType.AzureOpenAIAssistant],
        *,
        deployment_name: str | None = None,
        assistant_id: str | None = None,
        assistant_name: str | None = None,
        thread_id: str | None = None,
        api_key: str | None = None,
        endpoint: str | None = None,
        base_url: str | None = None,
        api_version: str | None = None,
        ad_token: str | None = None,
        ad_token_provider: object | None = None,
        token_endpoint: str | None = None,
        credential: object | None = None,
        default_headers: dict[str, str] | None = None,
        async_client: object | None = None,
        env_file_path: str | None = None,
        env_file_encoding: str | None = None,
    ) -> "AzureOpenAIAssistantsClient": ...

    @overload
    @staticmethod
    def create_client(  # noqa: E704
        client_type: type[ClientType.AzureOpenAIResponse],
        *,
        api_key: str | None = None,
        deployment_name: str | None = None,
        endpoint: str | None = None,
        base_url: str | None = None,
        api_version: str | None = None,
        ad_token: str | None = None,
        ad_token_provider: object | None = None,
        token_endpoint: str | None = None,
        credential: object | None = None,
        default_headers: dict[str, str] | None = None,
        async_client: object | None = None,
        env_file_path: str | None = None,
        env_file_encoding: str | None = None,
        instruction_role: str | None = None,
    ) -> "AzureOpenAIResponsesClient": ...

    @overload
    @staticmethod
    def create_client(  # noqa: E704
        client_type: type[ClientType.AzureOpenAIResponseWithRetry],
        *,
        api_key: str | None = None,
        deployment_name: str | None = None,
        endpoint: str | None = None,
        base_url: str | None = None,
        api_version: str | None = None,
        ad_token: str | None = None,
        ad_token_provider: object | None = None,
        token_endpoint: str | None = None,
        credential: object | None = None,
        default_headers: dict[str, str] | None = None,
        async_client: object | None = None,
        env_file_path: str | None = None,
        env_file_encoding: str | None = None,
        instruction_role: str | None = None,
        retry_config: RateLimitRetryConfig | None = None,
    ) -> AzureOpenAIResponseClientWithRetry: ...

    @overload
    @staticmethod
    def create_client(  # noqa: E704
        client_type: type[ClientType.AzureOpenAIAgent],
        *,
        project_client: object | None = None,
        agent_id: str | None = None,
        agent_name: str | None = None,
        thread_id: str | None = None,
        project_endpoint: str | None = None,
        model_deployment_name: str | None = None,
        async_credential: object | None = None,
        env_file_path: str | None = None,
        env_file_encoding: str | None = None,
    ) -> "AzureAIAgentClient": ...

    @staticmethod
    def create_client(
        client_type: ClientType,
        *,
        # Common Azure OpenAI parameters
        api_key: str | None = None,
        deployment_name: str | None = None,
        endpoint: str | None = None,
        base_url: str | None = None,
        api_version: str | None = None,
        ad_token: str | None = None,
        ad_token_provider: object | None = None,
        token_endpoint: str | None = None,
        credential: object | None = None,
        default_headers: dict[str, str] | None = None,
        async_client: object | None = None,
        env_file_path: str | None = None,
        env_file_encoding: str | None = None,
        # Chat & Response specific
        instruction_role: str | None = None,
        retry_config: RateLimitRetryConfig | None = None,
        # Assistant specific
        assistant_id: str | None = None,
        assistant_name: str | None = None,
        thread_id: str | None = None,
        # Azure AI Agent specific
        project_client: object | None = None,
        agent_id: str | None = None,
        agent_name: str | None = None,
        project_endpoint: str | None = None,
        model_deployment_name: str | None = None,
        async_credential: object | None = None,
    ):
        """Create an Agent Framework client instance.

        Args:
            client_type: The client type to construct.

            Common Azure OpenAI Parameters (Chat/Assistant/Response):
                api_key: Azure OpenAI API key (if not using Entra ID)
                deployment_name: Model deployment name
                endpoint: Azure OpenAI endpoint URL
                base_url: Azure OpenAI base URL (alternative to endpoint)
                api_version: Azure OpenAI API version
                ad_token: Azure AD token (static token)
                ad_token_provider: Azure AD token provider (dynamic token)
                token_endpoint: Token endpoint for Azure authentication
                credential: Azure TokenCredential for authentication
                default_headers: Default HTTP headers for requests
                async_client: Existing AsyncAzureOpenAI client to reuse
                env_file_path: Path to .env file for configuration
                env_file_encoding: Encoding of the .env file

            Chat & Response Specific:
                instruction_role: Role for instruction messages ('developer' or 'system')

            Assistant Specific:
                assistant_id: ID of existing assistant to use
                assistant_name: Name for new assistant
                thread_id: Default thread ID for conversations

            Azure AI Agent Specific:
                project_client: Existing AIProjectClient to use
                agent_id: ID of existing agent
                agent_name: Name for new agent
                project_endpoint: Azure AI Project endpoint URL
                model_deployment_name: Model deployment name for agent
                async_credential: Azure async credential for authentication

        Returns:
            The appropriate client instance with proper type binding

        Examples:
            # Chat Completion Client with minimal parameters
            chat_client = AFHelper.create_client(
                AgentType.AzureOpenAIChatCompletion,
                endpoint="https://your-endpoint.openai.azure.com/",
                deployment_name="gpt-4"
            )

            # Chat Completion Client with custom headers and instruction role
            chat_client = AFHelper.create_client(
                AgentType.AzureOpenAIChatCompletion,
                endpoint="https://your-endpoint.openai.azure.com/",
                deployment_name="gpt-4",
                api_version="2024-02-15-preview",
                instruction_role="developer",
                default_headers={"Custom-Header": "value"}
            )

            # Assistant Client with thread management
            assistant_client = AFHelper.create_client(
                AgentType.AzureOpenAIAssistant,
                endpoint="https://your-endpoint.openai.azure.com/",
                deployment_name="gpt-4",
                assistant_id="asst_123",
                thread_id="thread_456"
            )

            # Responses Client from .env file
            responses_client = AFHelper.create_client(
                AgentType.AzureOpenAIResponse,
                env_file_path="path/to/.env"
            )

            # Azure AI Agent Client
            agent_client = AFHelper.create_client(
                AgentType.AzureOpenAIAgent,
                project_endpoint="https://your-project.cognitiveservices.azure.com/",
                model_deployment_name="gpt-4",
                agent_name="MyAgent"
            )
        """
        # Use credential if provided, otherwise use ad_token_provider or default bearer token
        if not credential and not ad_token_provider:
            ad_token_provider = get_bearer_token_provider()

        if client_type == ClientType.OpenAIChatCompletion:
            raise NotImplementedError(
                "OpenAIChatClient is not implemented in this context."
            )
        elif client_type == ClientType.OpenAIAssistant:
            raise NotImplementedError(
                "OpenAIAssistantsClient is not implemented in this context."
            )
        elif client_type == ClientType.OpenAIResponse:
            raise NotImplementedError(
                "OpenAIResponsesClient is not implemented in this context."
            )
        elif client_type == ClientType.AzureOpenAIChatCompletion:
            from agent_framework.azure import AzureOpenAIChatClient

            return AzureOpenAIChatClient(
                api_key=api_key,
                deployment_name=deployment_name,
                endpoint=endpoint,
                base_url=base_url,
                api_version=api_version,
                ad_token=ad_token,
                ad_token_provider=ad_token_provider,
                token_endpoint=token_endpoint,
                credential=credential,
                default_headers=default_headers,
                async_client=async_client,
                env_file_path=env_file_path,
                env_file_encoding=env_file_encoding,
                instruction_role=instruction_role,
            )
        elif client_type == ClientType.AzureOpenAIChatCompletionWithRetry:
            return AzureOpenAIChatClientWithRetry(
                api_key=api_key,
                deployment_name=deployment_name,
                endpoint=endpoint,
                base_url=base_url,
                api_version=api_version,
                ad_token=ad_token,
                ad_token_provider=ad_token_provider,
                token_endpoint=token_endpoint,
                credential=credential,
                default_headers=default_headers,
                async_client=async_client,
                env_file_path=env_file_path,
                env_file_encoding=env_file_encoding,
                instruction_role=instruction_role,
                retry_config=retry_config,
            )
        elif client_type == ClientType.AzureOpenAIAssistant:
            from agent_framework.azure import AzureOpenAIAssistantsClient

            return AzureOpenAIAssistantsClient(
                deployment_name=deployment_name,
                assistant_id=assistant_id,
                assistant_name=assistant_name,
                thread_id=thread_id,
                api_key=api_key,
                endpoint=endpoint,
                base_url=base_url,
                api_version=api_version,
                ad_token=ad_token,
                ad_token_provider=ad_token_provider,
                token_endpoint=token_endpoint,
                credential=credential,
                default_headers=default_headers,
                async_client=async_client,
                env_file_path=env_file_path,
                env_file_encoding=env_file_encoding,
            )
        elif client_type == ClientType.AzureOpenAIResponse:
            from agent_framework.azure import AzureOpenAIResponsesClient

            return AzureOpenAIResponsesClient(
                api_key=api_key,
                deployment_name=deployment_name,
                endpoint=endpoint,
                base_url=base_url,
                api_version=api_version,
                ad_token=ad_token,
                ad_token_provider=ad_token_provider,
                token_endpoint=token_endpoint,
                credential=credential,
                default_headers=default_headers,
                async_client=async_client,
                env_file_path=env_file_path,
                env_file_encoding=env_file_encoding,
                instruction_role=instruction_role,
            )
        elif client_type == ClientType.AzureOpenAIResponseWithRetry:
            return AzureOpenAIResponseClientWithRetry(
                api_key=api_key,
                deployment_name=deployment_name,
                endpoint=endpoint,
                base_url=base_url,
                api_version=api_version,
                ad_token=ad_token,
                ad_token_provider=ad_token_provider,
                token_endpoint=token_endpoint,
                credential=credential,
                default_headers=default_headers,
                async_client=async_client,
                env_file_path=env_file_path,
                env_file_encoding=env_file_encoding,
                instruction_role=instruction_role,
                retry_config=retry_config,
            )
        elif client_type == ClientType.AzureOpenAIAgent:
            from agent_framework.azure import AzureAIAgentClient

            return AzureAIAgentClient(
                project_client=project_client,
                agent_id=agent_id,
                agent_name=agent_name,
                thread_id=thread_id,
                project_endpoint=project_endpoint,
                model_deployment_name=model_deployment_name,
                async_credential=async_credential,
                env_file_path=env_file_path,
                env_file_encoding=env_file_encoding,
            )
        else:
            raise ValueError(f"Unsupported agent type: {client_type}")
