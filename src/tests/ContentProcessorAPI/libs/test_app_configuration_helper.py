# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Unit tests for AppConfigurationHelper."""

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "ContentProcessorAPI")))

from app.libs.azure.app_configuration.helper import AppConfigurationHelper  # noqa: E402


@patch("app.libs.azure.app_configuration.helper.get_azure_credential")
@patch("app.libs.azure.app_configuration.helper.AzureAppConfigurationClient")
def test_app_configuration_helper_init(mock_client_class, mock_get_credential):
    """Test AppConfigurationHelper initialization."""
    mock_credential = MagicMock()
    mock_get_credential.return_value = mock_credential
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    endpoint = "https://test-endpoint.azconfig.io"
    helper = AppConfigurationHelper(endpoint)

    assert helper.app_config_endpoint == endpoint
    assert helper.credential == mock_credential
    mock_client_class.assert_called_once_with(
        endpoint,
        mock_credential,
        credential_scopes=["https://azconfig.io/.default"]
    )
    assert helper.app_config_client == mock_client


@patch("app.libs.azure.app_configuration.helper.get_azure_credential")
@patch("app.libs.azure.app_configuration.helper.AzureAppConfigurationClient")
def test_read_configuration(mock_client_class, mock_get_credential):
    """Test read_configuration method."""
    mock_credential = MagicMock()
    mock_get_credential.return_value = mock_credential
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    mock_settings = [MagicMock(key="key1", value="value1"), MagicMock(key="key2", value="value2")]
    mock_client.list_configuration_settings.return_value = mock_settings

    helper = AppConfigurationHelper("https://test-endpoint.azconfig.io")
    result = helper.read_configuration()

    assert result == mock_settings
    mock_client.list_configuration_settings.assert_called_once()


@patch("app.libs.azure.app_configuration.helper.get_azure_credential")
@patch("app.libs.azure.app_configuration.helper.AzureAppConfigurationClient")
@patch("app.libs.azure.app_configuration.helper.os.environ", {})
def test_read_and_set_environmental_variables(mock_client_class, mock_get_credential):
    """Test read_and_set_environmental_variables method."""
    mock_credential = MagicMock()
    mock_get_credential.return_value = mock_credential
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    mock_settings = [
        MagicMock(key="TEST_KEY1", value="test_value1"),
        MagicMock(key="TEST_KEY2", value="test_value2")
    ]
    mock_client.list_configuration_settings.return_value = mock_settings

    helper = AppConfigurationHelper("https://test-endpoint.azconfig.io")
    result = helper.read_and_set_environmental_variables()

    assert result["TEST_KEY1"] == "test_value1"
    assert result["TEST_KEY2"] == "test_value2"
