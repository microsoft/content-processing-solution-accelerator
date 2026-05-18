# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Lazy-initializing wrapper for mem0 AsyncMemory.

This module provides ``Mem0AsyncMemoryManager``, a thin singleton-style wrapper
that defers the creation of a ``mem0.AsyncMemory`` instance until first use.
The configuration is currently hardcoded to:

- **Vector store** — Redis on ``localhost:6379`` with 3 072-dim embeddings.
- **LLM** — Azure OpenAI ``gpt-5.1`` (low temperature, high token budget).
- **Embedder** — Azure OpenAI ``text-embedding-3-large``.

Design notes:
    - The manager is intended to be created once at application startup and shared
      across orchestrators via dependency injection.
    - ``get_memory()`` is idempotent — the underlying ``AsyncMemory`` is constructed
      exactly once and cached for subsequent calls.
    - The hardcoded configuration should eventually be externalized to environment
      variables or ``AgentFrameworkSettings``.
"""

from mem0 import AsyncMemory


class Mem0AsyncMemoryManager:
    """Lazy-initializing manager for a shared ``mem0.AsyncMemory`` instance.

    The manager follows a create-once / reuse-forever pattern:

    1. On first ``await get_memory()``, ``_create_memory()`` builds the
       ``AsyncMemory`` from a hardcoded configuration dict.
    2. Subsequent calls return the cached instance without reconstruction.

    This avoids expensive re-initialization (Redis connection, model loading)
    on every orchestrator invocation.
    """

    def __init__(self) -> None:
        """Create a manager with no memory instance yet.

        The actual ``AsyncMemory`` is created lazily on the first
        call to ``get_memory()``.
        """
        self._memory_instance: AsyncMemory | None = None

    async def get_memory(self) -> AsyncMemory:
        """Return the shared ``AsyncMemory``, creating it on first call.

        Returns:
            The singleton ``AsyncMemory`` instance configured with Redis
            vector store and Azure OpenAI LLM / embedder.
        """
        if self._memory_instance is None:
            self._memory_instance = await self._create_memory()
        return self._memory_instance

    async def _create_memory(self) -> AsyncMemory:
        """Build an ``AsyncMemory`` from hardcoded configuration.

        Configuration sections:
            1. **vector_store** — Redis at ``localhost:6379``, collection
               ``container_migration``, 3 072-dim embeddings.
            2. **llm** — Azure OpenAI ``gpt-5.1`` with low temperature.
            3. **embedder** — Azure OpenAI ``text-embedding-3-large``.

        Returns:
            A fully initialized ``AsyncMemory`` ready for search / add / get.
        """
        config = {
            "vector_store": {
                "provider": "redis",
                "config": {
                    "redis_url": "redis://localhost:6379",
                    "collection_name": "container_migration",
                    "embedding_model_dims": 3072,
                },
            },
            "llm": {
                "provider": "azure_openai",
                "config": {
                    "model": "gpt-5.1",
                    "temperature": 0.1,
                    "max_tokens": 100000,
                    "azure_kwargs": {
                        "azure_deployment": "gpt-5.1",
                        "api_version": "2024-12-01-preview",
                        "azure_endpoint": "https://aifappframework.cognitiveservices.azure.com/",
                    },
                },
            },
            "embedder": {
                "provider": "azure_openai",
                "config": {
                    "model": "text-embedding-3-large",
                    "azure_kwargs": {
                        "api_version": "2024-02-01",
                        "azure_deployment": "text-embedding-3-large",
                        "azure_endpoint": "https://aifappframework.openai.azure.com/",
                        "default_headers": {
                            "CustomHeader": "container migration",
                        },
                    },
                },
            },
            "version": "v1.1",
        }

        return await AsyncMemory.from_config(config)
