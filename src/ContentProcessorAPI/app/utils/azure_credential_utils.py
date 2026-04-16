# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Azure credential factory: selects DefaultAzureCredential (dev) vs ManagedIdentityCredential (prod)."""

import os

from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.identity.aio import (
    DefaultAzureCredential as AioDefaultAzureCredential,
)
from azure.identity.aio import (
    ManagedIdentityCredential as AioManagedIdentityCredential,
)


async def get_azure_credential_async(client_id=None):
    """Return an async Azure credential (DefaultAzureCredential in dev, ManagedIdentityCredential otherwise)."""
    if os.getenv("APP_ENV", "prod").lower() == "dev":
        return AioDefaultAzureCredential()  # CodeQL [SM05139] Okay use of DefaultAzureCredential as it is only used in development
    else:
        return AioManagedIdentityCredential(client_id=client_id)


def get_azure_credential(client_id=None):
    """Return a sync Azure credential (DefaultAzureCredential in dev, ManagedIdentityCredential otherwise)."""
    if os.getenv("APP_ENV", "prod").lower() == "dev":
        return DefaultAzureCredential()  # CodeQL [SM05139] Okay use of DefaultAzureCredential as it is only used in development
    else:
        return ManagedIdentityCredential(client_id=client_id)
