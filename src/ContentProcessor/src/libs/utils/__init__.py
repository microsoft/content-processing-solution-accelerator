# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Shared utility functions and helpers.

Sub-modules:
    azure_credential_utils: Azure credential selection for sync and async SDKs.
    base64_util: Base-64 encoding detection.
    credential_util: Convenience re-export of credential and token-provider
        helpers (mirrors azure_credential_utils).
    remote_module_loader: Dynamically load Python modules from Azure Blob
        Storage.
    stopwatch: Lightweight elapsed-time measurement context manager.
    utils: General-purpose JSON encoding, dict flattening, and value
        comparison helpers.
"""
