# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs.utils.azure_credential_utils (Azure credential factories)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import libs.utils.azure_credential_utils as azure_credential_utils

MODULE = "libs.utils.azure_credential_utils"


# ── get_azure_credential (sync) ─────────────────────────────────────────


@patch(f"{MODULE}.os.getenv")
@patch(f"{MODULE}.DefaultAzureCredential")
@patch(f"{MODULE}.ManagedIdentityCredential")
def test_get_azure_credential_dev_env(mock_managed, mock_default, mock_getenv):
    """Dev environment uses DefaultAzureCredential."""
    mock_getenv.return_value = "dev"
    mock_instance = MagicMock()
    mock_default.return_value = mock_instance

    credential = azure_credential_utils.get_azure_credential()

    mock_getenv.assert_called_once_with("APP_ENV", "prod")
    mock_default.assert_called_once()
    mock_managed.assert_not_called()
    assert credential == mock_instance


@patch(f"{MODULE}.os.getenv")
@patch(f"{MODULE}.DefaultAzureCredential")
@patch(f"{MODULE}.ManagedIdentityCredential")
def test_get_azure_credential_non_dev_env(mock_managed, mock_default, mock_getenv):
    """Non-dev environment uses ManagedIdentityCredential with client_id."""
    mock_getenv.return_value = "prod"
    mock_instance = MagicMock()
    mock_managed.return_value = mock_instance

    credential = azure_credential_utils.get_azure_credential(client_id="test-client-id")

    mock_getenv.assert_called_once_with("APP_ENV", "prod")
    mock_managed.assert_called_once_with(client_id="test-client-id")
    mock_default.assert_not_called()
    assert credential == mock_instance


# ── get_azure_credential_async ──────────────────────────────────────────


@pytest.mark.asyncio
@patch(f"{MODULE}.os.getenv")
@patch(f"{MODULE}.AioDefaultAzureCredential")
@patch(f"{MODULE}.AioManagedIdentityCredential")
async def test_get_azure_credential_async_dev_env(
    mock_aio_managed, mock_aio_default, mock_getenv
):
    """Dev environment uses async DefaultAzureCredential."""
    mock_getenv.return_value = "dev"
    mock_instance = MagicMock()
    mock_aio_default.return_value = mock_instance

    credential = await azure_credential_utils.get_azure_credential_async()

    mock_getenv.assert_called_once_with("APP_ENV", "prod")
    mock_aio_default.assert_called_once()
    mock_aio_managed.assert_not_called()
    assert credential == mock_instance


@pytest.mark.asyncio
@patch(f"{MODULE}.os.getenv")
@patch(f"{MODULE}.AioDefaultAzureCredential")
@patch(f"{MODULE}.AioManagedIdentityCredential")
async def test_get_azure_credential_async_non_dev_env(
    mock_aio_managed, mock_aio_default, mock_getenv
):
    """Non-dev environment uses async ManagedIdentityCredential with client_id."""
    mock_getenv.return_value = "prod"
    mock_instance = MagicMock()
    mock_aio_managed.return_value = mock_instance

    credential = await azure_credential_utils.get_azure_credential_async(
        client_id="test-client-id"
    )

    mock_getenv.assert_called_once_with("APP_ENV", "prod")
    mock_aio_managed.assert_called_once_with(client_id="test-client-id")
    mock_aio_default.assert_not_called()
    assert credential == mock_instance
