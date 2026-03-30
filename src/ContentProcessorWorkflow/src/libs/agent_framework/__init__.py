# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Agent Framework integration layer for the Content Processing workflow.

This package adapts the external ``agent_framework`` SDK into the content-processing
domain, providing:

Modules
-------
agent_builder
    Fluent builder and static factories for creating ``ChatAgent`` instances with
    chainable configuration (tools, temperature, middleware, etc.).
agent_framework_helper
    Client factory that initializes and caches Azure OpenAI / Response / Assistant /
    AI Agent clients based on ``AgentFrameworkSettings``.
agent_framework_settings
    Pydantic settings model that auto-discovers service endpoints from environment
    variables using configurable prefix conventions.
agent_info
    Lightweight Pydantic model carrying per-agent metadata (name, type, prompts,
    tools) with Jinja2 template rendering.
agent_speaking_capture
    ``AgentMiddleware`` that captures every agent response and dispatches sync/async
    callbacks — useful for streaming UIs and audit logging.
azure_openai_response_retry
    Rate-limit (HTTP 429) retry wrappers and context-window trimming logic for
    ``AzureOpenAIChatClient`` and ``AzureOpenAIResponsesClient``.
cosmos_checkpoint_storage
    Cosmos DB SQL API adapter implementing ``CheckpointStorage`` for durable
    workflow checkpoint persistence.
groupchat_orchestrator
    Generic ``GroupChatOrchestrator[TInput, TOutput]`` — the main execution engine
    that runs multi-agent GroupChat workflows with streaming callbacks, tool-call
    tracking, loop detection, and typed result generation.
mem0_async_memory
    Lazy-initializing wrapper around ``mem0.AsyncMemory`` with hardcoded Redis
    vector-store and Azure OpenAI embedder configuration.
middlewares
    Development / debugging middleware classes (``DebuggingMiddleware``,
    ``LoggingFunctionMiddleware``, ``InputObserverMiddleware``).
"""
