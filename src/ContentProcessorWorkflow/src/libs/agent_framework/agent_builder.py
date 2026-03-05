# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Fluent builder and static factories for ChatAgent construction.

This module provides ``AgentBuilder``, a single class offering two complementary
APIs for creating ``ChatAgent`` instances:

1. **Fluent builder** (recommended for readability):
   ``AgentBuilder(client).with_name(...).with_tools(...).build()``
2. **Static factory methods** (backward-compatible, parameter-heavy):
   ``AgentBuilder.create_agent(chat_client=..., name=..., tools=...)``
3. **AgentInfo-driven factory**:
   ``AgentBuilder.create_agent_by_agentinfo(service_id, agent_info, ...)``

Design decisions:
    - Every ``with_*()`` setter returns ``self`` for method chaining.
    - ``build()`` and the static factories all delegate to the ``ChatAgent``
      constructor; the builder simply accumulates keyword arguments.
    - ``create_agent_by_agentinfo`` resolves the chat client from the
      ``AgentFrameworkHelper`` attached to the ``AgentInfo``, so callers
      do not need to manage client construction themselves.

Supported configuration axes:
    - Model parameters: temperature, top_p, max_tokens, frequency/presence penalty.
    - Structured output: ``response_format`` (Pydantic model).
    - Tool binding: ``tools`` (MCP tools, callables, tool protocols, dicts).
    - Middleware: ``middleware`` (AgentMiddleware, ChatMiddleware, etc.).
    - Context providers: ``context_providers`` for injecting dynamic context.
    - Provider-specific options: ``additional_chat_options`` dict.
"""

from collections.abc import Callable, MutableMapping, Sequence
from typing import Any, Literal

from agent_framework import (
    AggregateContextProvider,
    ChatAgent,
    ChatClientProtocol,
    ChatMessageStoreProtocol,
    ContextProvider,
    Middleware,
    ToolMode,
    ToolProtocol,
)
from pydantic import BaseModel

from libs.agent_framework.agent_info import AgentInfo
from utils.credential_util import get_bearer_token_provider


class AgentBuilder:
    """Fluent builder for creating ChatAgent instances with a chainable API.

    This class provides two ways to create agents:
    1. Fluent API with method chaining (recommended for readability)
    2. Static factory methods (for backward compatibility)

    Examples:
        Fluent API (new style):

        .. code-block:: python

            agent = (
                AgentBuilder(client)
                .with_name("WeatherBot")
                .with_instructions("You are a weather assistant.")
                .with_tools([get_weather, get_location])
                .with_temperature(0.7)
                .with_max_tokens(500)
                .build()
            )

            async with agent:
                response = await agent.run("What's the weather?")

        Static factory (backward compatible):

        .. code-block:: python

            agent = AgentBuilder.create_agent(
                chat_client=client,
                name="WeatherBot",
                instructions="You are a weather assistant.",
                temperature=0.7
            )
    """

    def __init__(self, chat_client: ChatClientProtocol):
        """Initialize the builder with a chat client and default-None fields.

        All configuration is stored as private attributes.  None of them are
        set to non-trivial defaults here; the ``ChatAgent`` constructor applies
        its own defaults for any parameter that remains ``None``.

        Args:
            chat_client: The chat client protocol implementation (e.g.
                ``AzureOpenAIChatClient``, ``AzureOpenAIResponsesClient``).
        """
        self._chat_client = chat_client
        self._instructions: str | None = None
        self._id: str | None = None
        self._name: str | None = None
        self._description: str | None = None
        self._chat_message_store_factory: (
            Callable[[], ChatMessageStoreProtocol] | None
        ) = None
        self._conversation_id: str | None = None
        self._context_providers: (
            ContextProvider | list[ContextProvider] | AggregateContextProvider | None
        ) = None
        self._middleware: Middleware | list[Middleware] | None = None
        self._frequency_penalty: float | None = None
        self._logit_bias: dict[str | int, float] | None = None
        self._max_tokens: int | None = None
        self._metadata: dict[str, Any] | None = None
        self._model_id: str | None = None
        self._presence_penalty: float | None = None
        self._response_format: type[BaseModel] | None = None
        self._seed: int | None = None
        self._stop: str | Sequence[str] | None = None
        self._store: bool | None = None
        self._temperature: float | None = None
        self._tool_choice: (
            ToolMode | Literal["auto", "required", "none"] | dict[str, Any] | None
        ) = "auto"
        self._tools: (
            ToolProtocol
            | Callable[..., Any]
            | MutableMapping[str, Any]
            | Sequence[ToolProtocol | Callable[..., Any] | MutableMapping[str, Any]]
            | None
        ) = None
        self._top_p: float | None = None
        self._user: str | None = None
        self._additional_chat_options: dict[str, Any] | None = None
        self._kwargs: dict[str, Any] = {}

    def with_instructions(self, instructions: str) -> "AgentBuilder":
        """Set the agent's system instructions.

        Args:
            instructions: System instructions defining agent behavior

        Returns:
            Self for method chaining
        """
        self._instructions = instructions
        return self

    def with_id(self, id: str) -> "AgentBuilder":
        """Set the agent's unique identifier.

        Args:
            id: Unique identifier for the agent

        Returns:
            Self for method chaining
        """
        self._id = id
        return self

    def with_name(self, name: str) -> "AgentBuilder":
        """Set the agent's display name.

        Args:
            name: Display name for the agent

        Returns:
            Self for method chaining
        """
        self._name = name
        return self

    def with_description(self, description: str) -> "AgentBuilder":
        """Set the agent's description.

        Args:
            description: Description of the agent's purpose

        Returns:
            Self for method chaining
        """
        self._description = description
        return self

    def with_temperature(self, temperature: float) -> "AgentBuilder":
        """Set the sampling temperature (0.0 to 2.0).

        Args:
            temperature: Sampling temperature for response generation

        Returns:
            Self for method chaining
        """
        self._temperature = temperature
        return self

    def with_max_tokens(self, max_tokens: int) -> "AgentBuilder":
        """Set the maximum tokens in the response.

        Args:
            max_tokens: Maximum number of tokens to generate

        Returns:
            Self for method chaining
        """
        self._max_tokens = max_tokens
        return self

    def with_tools(
        self,
        tools: ToolProtocol
        | Callable[..., Any]
        | MutableMapping[str, Any]
        | Sequence[ToolProtocol | Callable[..., Any] | MutableMapping[str, Any]],
    ) -> "AgentBuilder":
        """Set the tools available to the agent.

        Args:
            tools: MCP tools, Python functions, or tool protocols

        Returns:
            Self for method chaining
        """
        self._tools = tools
        return self

    def with_tool_choice(
        self,
        tool_choice: ToolMode | Literal["auto", "required", "none"] | dict[str, Any],
    ) -> "AgentBuilder":
        """Set the tool selection mode.

        Args:
            tool_choice: Tool selection strategy

        Returns:
            Self for method chaining
        """
        self._tool_choice = tool_choice
        return self

    def with_middleware(
        self, middleware: Middleware | list[Middleware]
    ) -> "AgentBuilder":
        """Set middleware for request/response processing.

        Args:
            middleware: Middleware or list of middlewares

        Returns:
            Self for method chaining
        """
        self._middleware = middleware
        return self

    def with_context_providers(
        self,
        context_providers: ContextProvider
        | list[ContextProvider]
        | AggregateContextProvider,
    ) -> "AgentBuilder":
        """Set context providers for additional conversation context.

        Args:
            context_providers: Context provider(s) for enriching conversations

        Returns:
            Self for method chaining
        """
        self._context_providers = context_providers
        return self

    def with_conversation_id(self, conversation_id: str) -> "AgentBuilder":
        """Set the conversation ID for tracking.

        Args:
            conversation_id: ID for conversation tracking

        Returns:
            Self for method chaining
        """
        self._conversation_id = conversation_id
        return self

    def with_model_id(self, model_id: str) -> "AgentBuilder":
        """Set the specific model identifier.

        Args:
            model_id: Model identifier to use

        Returns:
            Self for method chaining
        """
        self._model_id = model_id
        return self

    def with_top_p(self, top_p: float) -> "AgentBuilder":
        """Set nucleus sampling parameter.

        Args:
            top_p: Nucleus sampling parameter (0.0 to 1.0)

        Returns:
            Self for method chaining
        """
        self._top_p = top_p
        return self

    def with_frequency_penalty(self, frequency_penalty: float) -> "AgentBuilder":
        """Set frequency penalty (-2.0 to 2.0).

        Args:
            frequency_penalty: Penalty for frequent token usage

        Returns:
            Self for method chaining
        """
        self._frequency_penalty = frequency_penalty
        return self

    def with_presence_penalty(self, presence_penalty: float) -> "AgentBuilder":
        """Set presence penalty (-2.0 to 2.0).

        Args:
            presence_penalty: Penalty for token presence

        Returns:
            Self for method chaining
        """
        self._presence_penalty = presence_penalty
        return self

    def with_seed(self, seed: int) -> "AgentBuilder":
        """Set random seed for deterministic outputs.

        Args:
            seed: Random seed value

        Returns:
            Self for method chaining
        """
        self._seed = seed
        return self

    def with_stop(self, stop: str | Sequence[str]) -> "AgentBuilder":
        """Set stop sequences for generation.

        Args:
            stop: Stop sequence(s)

        Returns:
            Self for method chaining
        """
        self._stop = stop
        return self

    def with_response_format(self, response_format: type[BaseModel]) -> "AgentBuilder":
        """Set Pydantic model for structured output.

        Args:
            response_format: Pydantic model class for response validation

        Returns:
            Self for method chaining
        """
        self._response_format = response_format
        return self

    def with_metadata(self, metadata: dict[str, Any]) -> "AgentBuilder":
        """Set additional metadata for the agent.

        Args:
            metadata: Metadata dictionary

        Returns:
            Self for method chaining
        """
        self._metadata = metadata
        return self

    def with_user(self, user: str) -> "AgentBuilder":
        """Set user identifier for tracking.

        Args:
            user: User identifier

        Returns:
            Self for method chaining
        """
        self._user = user
        return self

    def with_additional_chat_options(self, options: dict[str, Any]) -> "AgentBuilder":
        """Set provider-specific options.

        Args:
            options: Provider-specific chat options

        Returns:
            Self for method chaining
        """
        self._additional_chat_options = options
        return self

    def with_store(self, store: bool) -> "AgentBuilder":
        """Set whether to store conversation history.

        Args:
            store: Whether to store conversation

        Returns:
            Self for method chaining
        """
        self._store = store
        return self

    def with_message_store_factory(
        self, factory: Callable[[], ChatMessageStoreProtocol]
    ) -> "AgentBuilder":
        """Set the message store factory.

        Args:
            factory: Factory function to create message stores

        Returns:
            Self for method chaining
        """
        self._chat_message_store_factory = factory
        return self

    def with_logit_bias(self, logit_bias: dict[str | int, float]) -> "AgentBuilder":
        """Set logit bias to modify token likelihood.

        Args:
            logit_bias: Token ID to bias mapping

        Returns:
            Self for method chaining
        """
        self._logit_bias = logit_bias
        return self

    def with_kwargs(self, **kwargs: Any) -> "AgentBuilder":
        """Set additional keyword arguments.

        Args:
            **kwargs: Additional keyword arguments

        Returns:
            Self for method chaining
        """
        self._kwargs.update(kwargs)
        return self

    def build(self) -> ChatAgent:
        """Construct a ``ChatAgent`` from the accumulated configuration.

        Processing steps:
            1. Collect every attribute set via ``with_*()`` calls.
            2. Pass them as keyword arguments to ``ChatAgent(...)``.
            3. Return the fully constructed agent.

        The returned agent can be used directly or as an async context manager
        (``async with agent: ...``) when tools require lifecycle management.

        Returns:
            A ``ChatAgent`` instance ready for ``run()`` / ``run_stream()``.

        Example:
            .. code-block:: python

                agent = (
                    AgentBuilder(client)
                    .with_name("Assistant")
                    .with_instructions("You are helpful.")
                    .with_temperature(0.7)
                    .build()
                )

                async with agent:
                    response = await agent.run("Hello!")
        """
        return ChatAgent(
            chat_client=self._chat_client,
            instructions=self._instructions,
            id=self._id,
            name=self._name,
            description=self._description,
            chat_message_store_factory=self._chat_message_store_factory,
            conversation_id=self._conversation_id,
            context_providers=self._context_providers,
            middleware=self._middleware,
            frequency_penalty=self._frequency_penalty,
            logit_bias=self._logit_bias,
            max_tokens=self._max_tokens,
            metadata=self._metadata,
            model_id=self._model_id,
            presence_penalty=self._presence_penalty,
            response_format=self._response_format,
            seed=self._seed,
            stop=self._stop,
            store=self._store,
            temperature=self._temperature,
            tool_choice=self._tool_choice,
            tools=self._tools,
            top_p=self._top_p,
            user=self._user,
            additional_chat_options=self._additional_chat_options,
            **self._kwargs,
        )

    @staticmethod
    def create_agent_by_agentinfo(
        service_id: str,
        agent_info: AgentInfo,
        *,
        id: str | None = None,
        chat_message_store_factory: Callable[[], ChatMessageStoreProtocol]
        | None = None,
        conversation_id: str | None = None,
        context_providers: ContextProvider
        | list[ContextProvider]
        | AggregateContextProvider
        | None = None,
        middleware: Middleware | list[Middleware] | None = None,
        frequency_penalty: float | None = None,
        logit_bias: dict[str | int, float] | None = None,
        max_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
        model_id: str | None = None,
        presence_penalty: float | None = None,
        response_format: type[BaseModel] | None = None,
        seed: int | None = None,
        stop: str | Sequence[str] | None = None,
        store: bool | None = None,
        temperature: float | None = None,
        tool_choice: ToolMode
        | Literal["auto", "required", "none"]
        | dict[str, Any]
        | None = "auto",
        tools: ToolProtocol
        | Callable[..., Any]
        | MutableMapping[str, Any]
        | Sequence[ToolProtocol | Callable[..., Any] | MutableMapping[str, Any]]
        | None = None,
        top_p: float | None = None,
        user: str | None = None,
        additional_chat_options: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> ChatAgent:
        """Create a ``ChatAgent`` from an ``AgentInfo`` metadata bundle.

        This factory resolves the chat client automatically by reading the
        ``AgentFrameworkHelper`` and ``ServiceConfig`` attached to the given
        ``AgentInfo``.  It is the preferred entry point for orchestrators that
        define agents declaratively via ``AgentInfo`` objects.

        Processing steps:
            1. Extract ``agent_framework_helper`` from ``agent_info``.
            2. Look up the ``ServiceConfig`` for ``service_id``.
            3. Call ``create_client()`` with the config’s endpoint, deployment,
               API version, and Entra ID token provider.
            4. Resolve instructions (``agent_instruction`` preferred over
               ``agent_system_prompt``).
            5. Delegate to ``AgentBuilder.create_agent()`` with the resolved
               client and all remaining parameters.

        Args:
            service_id: The service ID to use for getting the client configuration
            agent_info: AgentInfo configuration object containing agent settings
            id: Unique identifier for the agent
            chat_message_store_factory: Factory function to create message stores
            conversation_id: ID for conversation tracking
            context_providers: Providers for additional context in conversations
            middleware: Middleware for request/response processing
            frequency_penalty: Penalize frequent token usage (-2.0 to 2.0)
            logit_bias: Modify likelihood of specific tokens
            max_tokens: Maximum tokens in the response
            metadata: Additional metadata for the agent
            model_id: Specific model identifier to use
            presence_penalty: Penalize token presence (-2.0 to 2.0)
            response_format: Pydantic model for structured output
            seed: Random seed for deterministic outputs
            stop: Stop sequences for generation
            store: Whether to store conversation history
            temperature: Sampling temperature (0.0 to 2.0)
            tool_choice: Tool selection mode
            tools: Tools available to the agent (MCP tools, callables, or tool protocols)
            top_p: Nucleus sampling parameter
            user: User identifier for tracking
            additional_chat_options: Provider-specific options
            **kwargs: Additional keyword arguments

        Returns:
            ChatAgent: Configured agent instance ready for use

        Example:
            .. code-block:: python

                agent_info = AgentInfo(
                    agent_name="WeatherBot",
                    agent_type=ClientType.AZURE_OPENAI,
                    agent_instruction="You are a weather assistant.",
                    agent_framework_helper=af_helper,
                )

                agent = await AgentBuilder.create_agent_by_agentinfo(
                    service_id="default",
                    agent_info=agent_info,
                    tools=[weather_tool, get_location],
                    temperature=0.7,
                    max_tokens=500,
                )
        """

        agent_framework_helper = agent_info.agent_framework_helper
        if agent_framework_helper is None or agent_framework_helper.settings is None:
            raise ValueError("AgentFrameworkHelper settings cannot be None.")
        service_config = agent_framework_helper.settings.get_service_config(service_id)
        if service_config is None:
            raise ValueError(f"Service config for {service_id} not found.")

        agent_client = agent_framework_helper.create_client(
            client_type=agent_info.agent_type,
            endpoint=service_config.endpoint,
            deployment_name=service_config.chat_deployment_name,
            api_version=service_config.api_version,
            ad_token_provider=get_bearer_token_provider(),
        )

        # Use agent_instruction if available, fallback to agent_system_prompt
        instructions = agent_info.agent_instruction or agent_info.agent_system_prompt

        return AgentBuilder.create_agent(
            chat_client=agent_client,
            instructions=instructions,
            id=id,
            name=agent_info.agent_name,
            description=agent_info.agent_description,
            chat_message_store_factory=chat_message_store_factory,
            conversation_id=conversation_id,
            context_providers=context_providers,
            middleware=middleware,
            frequency_penalty=frequency_penalty,
            logit_bias=logit_bias,
            max_tokens=max_tokens,
            metadata=metadata,
            model_id=model_id,
            presence_penalty=presence_penalty,
            response_format=response_format,
            seed=seed,
            stop=stop,
            store=store,
            temperature=temperature,
            tool_choice=tool_choice,
            tools=tools,
            top_p=top_p,
            user=user,
            additional_chat_options=additional_chat_options,
            **kwargs,
        )

    @staticmethod
    def create_agent(
        chat_client: ChatClientProtocol,
        instructions: str | None = None,
        *,
        id: str | None = None,
        name: str | None = None,
        description: str | None = None,
        chat_message_store_factory: Callable[[], ChatMessageStoreProtocol]
        | None = None,
        conversation_id: str | None = None,
        context_providers: ContextProvider
        | list[ContextProvider]
        | AggregateContextProvider
        | None = None,
        middleware: Middleware | list[Middleware] | None = None,
        frequency_penalty: float | None = None,
        logit_bias: dict[str | int, float] | None = None,
        max_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
        model_id: str | None = None,
        presence_penalty: float | None = None,
        response_format: type[BaseModel] | None = None,
        seed: int | None = None,
        stop: str | Sequence[str] | None = None,
        store: bool | None = None,
        temperature: float | None = None,
        tool_choice: ToolMode
        | Literal["auto", "required", "none"]
        | dict[str, Any]
        | None = "auto",
        tools: ToolProtocol
        | Callable[..., Any]
        | MutableMapping[str, Any]
        | Sequence[ToolProtocol | Callable[..., Any] | MutableMapping[str, Any]]
        | None = None,
        top_p: float | None = None,
        user: str | None = None,
        additional_chat_options: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> ChatAgent:
        """Create a Chat Client Agent.

        Factory method that creates a ChatAgent instance with the specified configuration.
        The agent uses a chat client to interact with language models and supports tools
        (MCP tools, callable functions), context providers, middleware, and both streaming
        and non-streaming responses.

        Args:
            chat_client: The chat client protocol implementation (e.g., OpenAI, Azure OpenAI)
            instructions: System instructions for the agent's behavior
            id: Unique identifier for the agent
            name: Display name for the agent
            description: Description of the agent's purpose
            chat_message_store_factory: Factory function to create message stores
            conversation_id: ID for conversation tracking
            context_providers: Providers for additional context in conversations
            middleware: Middleware for request/response processing
            frequency_penalty: Penalize frequent token usage (-2.0 to 2.0)
            logit_bias: Modify likelihood of specific tokens
            max_tokens: Maximum tokens in the response
            metadata: Additional metadata for the agent
            model_id: Specific model identifier to use
            presence_penalty: Penalize token presence (-2.0 to 2.0)
            response_format: Pydantic model for structured output
            seed: Random seed for deterministic outputs
            stop: Stop sequences for generation
            store: Whether to store conversation history
            temperature: Sampling temperature (0.0 to 2.0)
            tool_choice: Tool selection mode ("auto", "required", "none", or specific tool)
            tools: Tools available to the agent (MCP tools, callables, or tool protocols)
            top_p: Nucleus sampling parameter
            user: User identifier for tracking
            additional_chat_options: Provider-specific options
            **kwargs: Additional keyword arguments

        Returns:
            ChatAgent: Configured chat agent instance that can be used directly or with async context manager

        Examples:
            Non-streaming example (from azure_response_client_basic.py):

            .. code-block:: python

                from libs.agent_framework.agent_builder import AgentBuilder

                ai_response_client = await self.agent_framework_helper.get_client_async("default")

                async with AgentBuilder.create_agent(
                    chat_client=ai_response_client,
                    name="WeatherAgent",
                    instructions="You are a helpful weather agent.",
                    tools=self.get_weather,
                ) as agent:
                    query = "What's the weather like in Seattle?"
                    result = await agent.run(query)
                    print(f"Agent: {result}")

            Streaming example (from azure_response_client_basic.py):

            .. code-block:: python

                async with AgentBuilder.create_agent(
                    chat_client=ai_response_client,
                    name="WeatherAgent",
                    instructions="You are a helpful weather agent.",
                    tools=self.get_weather,
                ) as agent:
                    query = "What's the weather like in Seattle?"
                    async for chunk in agent.run_stream(query):
                        if chunk.text:
                            print(chunk.text, end="", flush=True)

            With temperature and max_tokens:

            .. code-block:: python

                agent = AgentBuilder.create_agent(
                    chat_client=client,
                    name="reasoning-agent",
                    instructions="You are a reasoning assistant.",
                    temperature=0.7,
                    max_tokens=500,
                )

                # Use with async context manager for proper cleanup
                async with agent:
                    response = await agent.run("Explain quantum mechanics")
                    print(response.text)

            With provider-specific options:

            .. code-block:: python

                agent = AgentBuilder.create_agent(
                    chat_client=client,
                    name="reasoning-agent",
                    instructions="You are a reasoning assistant.",
                    model_id="gpt-4",
                    temperature=0.7,
                    max_tokens=500,
                    additional_chat_options={
                        "reasoning": {"effort": "high", "summary": "concise"}
                    },  # OpenAI-specific reasoning options
                )

                async with agent:
                    response = await agent.run("How do you prove the Pythagorean theorem?")
                    print(response.text)

        Note:
            When the agent has MCP tools or needs proper resource cleanup, use it with
            ``async with`` to ensure proper initialization and cleanup via the ChatAgent's
            async context manager protocol.
        """
        return ChatAgent(
            chat_client=chat_client,
            instructions=instructions,
            id=id,
            name=name,
            description=description,
            chat_message_store_factory=chat_message_store_factory,
            conversation_id=conversation_id,
            context_providers=context_providers,
            middleware=middleware,
            frequency_penalty=frequency_penalty,
            logit_bias=logit_bias,
            max_tokens=max_tokens,
            metadata=metadata,
            model_id=model_id,
            presence_penalty=presence_penalty,
            response_format=response_format,
            seed=seed,
            stop=stop,
            store=store,
            temperature=temperature,
            tool_choice=tool_choice,
            tools=tools,
            top_p=top_p,
            user=user,
            additional_chat_options=additional_chat_options,
            **kwargs,
        )
