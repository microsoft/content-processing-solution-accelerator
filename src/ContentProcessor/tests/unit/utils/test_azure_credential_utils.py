# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs.utils.azure_credential_utils (Azure credential factories)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import libs.utils.azure_credential_utils as azure_credential_utils

MODULE = "libs.utils.azure_credential_utils"


# ── TestGetAzureCredential ──────────────────────────────────────────────


class TestGetAzureCredential:
    """Synchronous get_azure_credential() factory tests."""

    @patch(f"{MODULE}.AzureCliCredential")
    @patch.dict("os.environ", {}, clear=True)
    def test_returns_cli_in_local_env(self, mock_cli_credential):
        mock_instance = MagicMock()
        mock_cli_credential.return_value = mock_instance
        credential = azure_credential_utils.get_azure_credential()
        mock_cli_credential.assert_called_once()
        assert credential == mock_instance

    @patch(f"{MODULE}.ManagedIdentityCredential")
    @patch.dict("os.environ", {"IDENTITY_ENDPOINT": "https://fake"}, clear=True)
    def test_returns_system_assigned_in_azure_env(self, mock_managed):
        mock_instance = MagicMock()
        mock_managed.return_value = mock_instance
        credential = azure_credential_utils.get_azure_credential()
        mock_managed.assert_called_once_with()
        assert credential == mock_instance

    @patch(f"{MODULE}.ManagedIdentityCredential")
    @patch.dict("os.environ", {"AZURE_CLIENT_ID": "test-client-id"}, clear=True)
    def test_returns_user_assigned_with_client_id(self, mock_managed):
        mock_instance = MagicMock()
        mock_managed.return_value = mock_instance
        credential = azure_credential_utils.get_azure_credential()
        mock_managed.assert_called_once_with(client_id="test-client-id")
        assert credential == mock_instance

    @patch(f"{MODULE}.DefaultAzureCredential")
    @patch(f"{MODULE}.AzureDeveloperCliCredential", side_effect=Exception("no azd"))
    @patch(f"{MODULE}.AzureCliCredential", side_effect=Exception("no az"))
    @patch.dict("os.environ", {}, clear=True)
    def test_falls_back_to_default(self, mock_cli, mock_dev_cli, mock_default):
        mock_instance = MagicMock()
        mock_default.return_value = mock_instance
        credential = azure_credential_utils.get_azure_credential()
        mock_default.assert_called_once()
        assert credential == mock_instance


# ── TestGetAsyncAzureCredential ─────────────────────────────────────────


class TestGetAsyncAzureCredential:
    """Async get_async_azure_credential() factory tests."""

    @patch(f"{MODULE}.AsyncAzureCliCredential")
    @patch.dict("os.environ", {}, clear=True)
    def test_returns_async_cli_in_local_env(self, mock_async_cli):
        mock_instance = MagicMock()
        mock_async_cli.return_value = mock_instance
        credential = azure_credential_utils.get_async_azure_credential()
        mock_async_cli.assert_called_once()
        assert credential == mock_instance

    @patch(f"{MODULE}.AsyncManagedIdentityCredential")
    @patch.dict("os.environ", {"IDENTITY_ENDPOINT": "https://fake"}, clear=True)
    def test_returns_async_system_assigned_in_azure_env(self, mock_async_managed):
        mock_instance = MagicMock()
        mock_async_managed.return_value = mock_instance
        credential = azure_credential_utils.get_async_azure_credential()
        mock_async_managed.assert_called_once_with()
        assert credential == mock_instance

    @patch(f"{MODULE}.AsyncManagedIdentityCredential")
    @patch.dict("os.environ", {"AZURE_CLIENT_ID": "test-client-id"}, clear=True)
    def test_returns_async_user_assigned_with_client_id(self, mock_async_managed):
        mock_instance = MagicMock()
        mock_async_managed.return_value = mock_instance
        credential = azure_credential_utils.get_async_azure_credential()
        mock_async_managed.assert_called_once_with(client_id="test-client-id")
        assert credential == mock_instance

    @patch(f"{MODULE}.AsyncDefaultAzureCredential")
    @patch(
        f"{MODULE}.AsyncAzureDeveloperCliCredential",
        side_effect=Exception("no azd"),
    )
    @patch(f"{MODULE}.AsyncAzureCliCredential", side_effect=Exception("no az"))
    @patch.dict("os.environ", {}, clear=True)
    def test_falls_back_to_async_default(
        self, mock_async_cli, mock_async_dev_cli, mock_async_default
    ):
        mock_instance = MagicMock()
        mock_async_default.return_value = mock_instance
        credential = azure_credential_utils.get_async_azure_credential()
        mock_async_default.assert_called_once()
        assert credential == mock_instance
