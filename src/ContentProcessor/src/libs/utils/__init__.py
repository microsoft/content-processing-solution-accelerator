# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Shared utility functions and helpers.

Sub-modules:
    azure_credential_utils: Azure credential selection for sync and async SDKs.
    base64_util: Base-64 encoding detection.
    credential_util: Convenience re-export of credential and token-provider
        helpers (mirrors azure_credential_utils).
    remote_schema_loader: Materialise Pydantic models from JSON Schema
        descriptors stored in Azure Blob Storage (no code execution).
    stopwatch: Lightweight elapsed-time measurement context manager.
    utils: General-purpose JSON encoding, dict flattening, and value
        comparison helpers.
"""
