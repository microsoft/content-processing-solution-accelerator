# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Azure credential selection helpers.

This module centralizes credential selection for Azure SDK clients.

Operational behavior:
        - In Azure-hosted environments, prefer managed identity (RBAC-based auth).
        - In local development, prefer CLI-backed credentials ("az" / "azd").
        - Provide both sync and async credential helpers for SDKs that require
            async authentication.
"""

import logging
import os
from typing import Any

from azure.identity import (
    AzureCliCredential,
    AzureDeveloperCliCredential,
    DefaultAzureCredential,
    ManagedIdentityCredential,
)
from azure.identity import (
    get_bearer_token_provider as identity_get_bearer_token_provider,
)
from azure.identity.aio import (
    AzureCliCredential as AsyncAzureCliCredential,
)
from azure.identity.aio import (
    AzureDeveloperCliCredential as AsyncAzureDeveloperCliCredential,
)
from azure.identity.aio import (
    DefaultAzureCredential as AsyncDefaultAzureCredential,
)
from azure.identity.aio import (
    ManagedIdentityCredential as AsyncManagedIdentityCredential,
)
from azure.identity.aio import (
    get_bearer_token_provider as identity_get_async_bearer_token_provider,
)


async def get_async_bearer_token_provider():
    """Return a bearer token provider for async Azure SDK clients.

    Returns:
        A callable suitable for SDK clients that accept a token provider.
    """
    credential = await get_async_azure_credential()
    return identity_get_async_bearer_token_provider(
        credential, "https://cognitiveservices.azure.com/.default"
    )


def get_bearer_token_provider():
    """Return a bearer token provider for sync Azure SDK clients.

    Returns:
        A callable suitable for SDK clients that accept a token provider.
    """
    credential = get_azure_credential()
    return identity_get_bearer_token_provider(
        credential, "https://cognitiveservices.azure.com/.default"
    )


def get_azure_credential():
    """Return the best Azure credential for the current runtime environment.

    Operational preference order:
        1) Azure-hosted: managed identity (system- or user-assigned)
        2) Local: Azure CLI and Azure Developer CLI credentials
        3) Fallback: DefaultAzureCredential
    """

    # Check if running in Azure environment (container, app service, VM, etc.)
    azure_env_indicators = [
        "WEBSITE_SITE_NAME",  # App Service
        "AZURE_CLIENT_ID",  # User-assigned managed identity
        "MSI_ENDPOINT",  # System-assigned managed identity
        "IDENTITY_ENDPOINT",  # Newer managed identity endpoint
        "KUBERNETES_SERVICE_HOST",  # AKS container
        "CONTAINER_REGISTRY_LOGIN",  # Azure Container Registry
    ]

    # Check for checking current environment - Hoster (Azure / Cli on Local)
    if any(os.getenv(indicator) for indicator in azure_env_indicators):
        logging.info(
            "[AUTH] Detected Azure environment - using ManagedIdentityCredential for role-based auth"
        )

        client_id = os.getenv("AZURE_CLIENT_ID")
        if client_id:
            logging.info(f"[AUTH] Using user-assigned managed identity: {client_id}")
            return ManagedIdentityCredential(client_id=client_id)
        else:
            logging.info("[AUTH] Using system-assigned managed identity")
            return ManagedIdentityCredential()

    # Local development - try multiple CLI credentials
    credential_attempts = []

    # Try Azure CLI as Default (traditional)
    try:
        logging.info("[AUTH] Trying AzureCliCredential (requires 'az login')")
        credential = AzureCliCredential()
        credential_attempts.append(("AzureCliCredential", credential))
    except Exception as e:
        logging.warning(f"[AUTH] AzureCliCredential failed: {e}")

    # Try Azure Developer CLI Second (newer, designed for development)
    try:
        logging.info(
            "[AUTH] Local development detected - trying AzureDeveloperCliCredential (requires 'azd auth login')"
        )
        credential = AzureDeveloperCliCredential()
        credential_attempts.append(("AzureDeveloperCliCredential", credential))
    except Exception as e:
        logging.warning(f"[AUTH] AzureDeveloperCliCredential failed: {e}")

    # Return the first successful credential
    if credential_attempts:
        credential_name, credential = credential_attempts[0]
        logging.info(f"[AUTH] Using {credential_name} for local development")
        return credential

    # Final fallback to DefaultAzureCredential
    logging.info(
        "[AUTH] All CLI credentials failed - falling back to DefaultAzureCredential"
    )
    return DefaultAzureCredential()


def get_async_azure_credential():
    """Return the best async Azure credential for the current runtime environment."""

    azure_env_indicators = [
        "WEBSITE_SITE_NAME",  # App Service
        "AZURE_CLIENT_ID",  # User-assigned managed identity
        "MSI_ENDPOINT",  # System-assigned managed identity
        "IDENTITY_ENDPOINT",  # Newer managed identity endpoint
        "KUBERNETES_SERVICE_HOST",  # AKS container
        "CONTAINER_REGISTRY_LOGIN",  # Azure Container Registry
    ]

    if any(os.getenv(indicator) for indicator in azure_env_indicators):
        logging.info(
            "[AUTH] Detected Azure environment - using async ManagedIdentityCredential for role-based auth"
        )

        client_id = os.getenv("AZURE_CLIENT_ID")
        if client_id:
            logging.info(
                f"[AUTH] Using async user-assigned managed identity: {client_id}"
            )
            return AsyncManagedIdentityCredential(client_id=client_id)
        else:
            logging.info("[AUTH] Using async system-assigned managed identity")
            return AsyncManagedIdentityCredential()

    # Local development - try multiple CLI credentials
    credential_attempts = []

    # Try Azure CLI as default (traditional)
    try:
        logging.info("[AUTH] Trying async AzureCliCredential (requires 'az login')")
        credential = AsyncAzureCliCredential()
        credential_attempts.append(("AsyncAzureCliCredential", credential))
    except Exception as e:
        logging.warning(f"[AUTH] AsyncAzureCliCredential failed: {e}")

    # Try Azure Developer CLI (newer, designed for development)
    try:
        logging.info(
            "[AUTH] Local development detected - trying async AzureDeveloperCliCredential (requires 'azd auth login')"
        )
        credential = AsyncAzureDeveloperCliCredential()
        credential_attempts.append(("AsyncAzureDeveloperCliCredential", credential))
    except Exception as e:
        logging.warning(f"[AUTH] AsyncAzureDeveloperCliCredential failed: {e}")

    # Return the first successful credential
    if credential_attempts:
        credential_name, credential = credential_attempts[0]
        logging.info(f"[AUTH] Using {credential_name} for local development")
        return credential

    # Final fallback to DefaultAzureCredential
    logging.info(
        "[AUTH] All async CLI credentials failed - falling back to AsyncDefaultAzureCredential"
    )
    return AsyncDefaultAzureCredential()


def validate_azure_authentication() -> dict[str, Any]:
    """Validate Azure authentication configuration and return diagnostics.

    Returns:
        JSON-serializable diagnostic payload including environment indicators,
        chosen credential type, and actionable recommendations.
    """
    import os

    auth_info = {
        "status": "unknown",
        "credential_type": "none",
        "environment": "unknown",
        "recommendations": [],
        "azure_env_indicators": {},
    }

    # Check environment indicators
    azure_indicators = {
        "WEBSITE_SITE_NAME": os.getenv("WEBSITE_SITE_NAME"),
        "AZURE_CLIENT_ID": os.getenv("AZURE_CLIENT_ID"),
        "MSI_ENDPOINT": os.getenv("MSI_ENDPOINT"),
        "IDENTITY_ENDPOINT": os.getenv("IDENTITY_ENDPOINT"),
        "KUBERNETES_SERVICE_HOST": os.getenv("KUBERNETES_SERVICE_HOST"),
    }

    auth_info["azure_env_indicators"] = {k: v for k, v in azure_indicators.items() if v}

    if any(azure_indicators.values()):
        auth_info["environment"] = "azure_hosted"
        auth_info["credential_type"] = "managed_identity"
        if os.getenv("AZURE_CLIENT_ID"):
            auth_info["recommendations"].append(
                "Using user-assigned managed identity - ensure proper RBAC roles assigned"
            )
        else:
            auth_info["recommendations"].append(
                "Using system-assigned managed identity - ensure it's enabled and has proper RBAC roles"
            )
    else:
        auth_info["environment"] = "local_development"
        auth_info["credential_type"] = "cli_credentials"
        auth_info["recommendations"].extend([
            "For local development, authenticate using one of:",
            "  • Azure Developer CLI: 'azd auth login' (recommended for development)",
            "  • Azure CLI: 'az login' (traditional method)",
            "Both methods are supported and will be tried automatically",
            "Ensure you have access to required Azure resources",
            "Consider using 'az account show' to verify current subscription",
        ])

    try:
        credential = get_azure_credential()
        auth_info["status"] = "configured"
        auth_info["credential_instance"] = type(credential).__name__
    except Exception as e:
        auth_info["status"] = "error"
        auth_info["error"] = str(e)
        auth_info["recommendations"].append(f"Authentication setup failed: {e}")

    return auth_info
