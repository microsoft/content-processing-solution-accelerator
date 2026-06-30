# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Base classes for Content Processing workflow applications.

Modules:
    application_base
        ``ApplicationBase`` -- abstract base class that every top-level
        service inherits from.  It owns the full bootstrap sequence:
        ``.env`` loading, Azure App Configuration hydration, credential
        setup, logging configuration, and LLM settings initialisation.
"""
