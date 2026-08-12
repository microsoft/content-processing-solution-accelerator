# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Azure credential factory: selects DefaultAzureCredential (dev) vs ManagedIdentityCredential (prod)."""

import os

from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.identity import (
    get_bearer_token_provider as identity_get_bearer_token_provider,
)
from azure.identity.aio import (
    DefaultAzureCredential as AioDefaultAzureCredential,
)
from azure.identity.aio import (
    ManagedIdentityCredential as AioManagedIdentityCredential,
)
from azure.identity.aio import (
    get_bearer_token_provider as identity_get_async_bearer_token_provider,
)


def get_azure_credential(client_id=None):
    """Return a sync Azure credential (DefaultAzureCredential in dev, ManagedIdentityCredential otherwise)."""
    if os.getenv("APP_ENV", "prod").lower() == "dev":
        return DefaultAzureCredential()  # CodeQL [SM05139] Okay use of DefaultAzureCredential as it is only used in development
    return ManagedIdentityCredential(client_id=client_id)


async def get_azure_credential_async(client_id=None):
    """Return an async Azure credential (DefaultAzureCredential in dev, ManagedIdentityCredential otherwise)."""
    if os.getenv("APP_ENV", "prod").lower() == "dev":
        return AioDefaultAzureCredential()  # CodeQL [SM05139] Okay use of DefaultAzureCredential as it is only used in development
    return AioManagedIdentityCredential(client_id=client_id)


def get_bearer_token_provider():
    """Return a bearer token provider for sync Azure SDK clients."""
    credential = get_azure_credential()
    return identity_get_bearer_token_provider(
        credential, "https://cognitiveservices.azure.com/.default"
    )


async def get_async_bearer_token_provider():
    """Return a bearer token provider for async Azure SDK clients."""
    credential = await get_azure_credential_async()
    return identity_get_async_bearer_token_provider(
        credential, "https://cognitiveservices.azure.com/.default"
    )
