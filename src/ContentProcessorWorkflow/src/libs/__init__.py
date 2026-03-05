# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Shared libraries for the Content Processing workflow.

Sub-packages:
    agent_framework
        Multi-agent orchestration built on Semantic Kernel — agent
        builders, group-chat orchestrators, checkpoint storage, retry
        middleware, and telemetry capture.

    application
        Configuration hierarchy (Pydantic ``BaseSettings``), the
        ``AppContext`` dependency-injection container, and per-deployment
        ``ServiceConfig`` descriptors for Azure OpenAI.

    azure
        Thin helpers for Azure platform services.  Currently contains
        ``AppConfigurationHelper`` for hydrating ``os.environ`` from
        Azure App Configuration at startup.

    base
        ``ApplicationBase`` — abstract class that owns the full bootstrap
        sequence (``.env`` loading, credential setup, App Configuration
        pull, logging, and LLM settings initialisation).
"""
