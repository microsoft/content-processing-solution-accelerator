# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Application framework — configuration, dependency injection, and service lifecycle.

This package provides the foundational infrastructure that every service in the
Content Processing pipeline depends on:

Modules:
    application_configuration
        Pydantic-based settings hierarchy that merges environment variables,
        ``.env`` files, and Azure App Configuration into a single typed
        ``Configuration`` object.

    application_context
        Full-featured dependency-injection container (``AppContext``) with
        singleton, transient, scoped, and async lifetime support, plus
        Azure ``DefaultAzureCredential`` integration.

    service_config
        Lightweight data class (``ServiceConfig``) that normalises the
        environment variables needed by a single Azure OpenAI deployment
        into a validated, dictionary-serialisable descriptor.

Typical bootstrap sequence::

    from libs.application.application_configuration import Configuration
    from libs.application.application_context import AppContext

    config = Configuration()                     # loads .env + env vars
    ctx = AppContext()
    ctx.set_configuration(config)
    ctx.set_credential(DefaultAzureCredential())

    ctx.add_singleton(IMyService, MyServiceImpl)
    service = ctx.get_service(IMyService)
"""
