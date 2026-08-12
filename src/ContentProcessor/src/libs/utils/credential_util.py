# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Convenience re-exports of Azure credential and token-provider helpers.

Mirrors :mod:`libs.utils.azure_credential_utils`.
"""

from libs.utils.azure_credential_utils import (
    get_async_bearer_token_provider,
    get_azure_credential,
    get_azure_credential_async,
    get_bearer_token_provider,
)

__all__ = [
    "get_async_bearer_token_provider",
    "get_azure_credential",
    "get_azure_credential_async",
    "get_bearer_token_provider",
]
