import os
import pytest
from unittest.mock import patch
from azure.appconfiguration import ConfigurationSetting
from app.libs.app_configuration.helper import AppConfigurationHelper


@pytest.fixture
def mock_app_config_client():
    with patch(
        "app.libs.app_configuration.helper.AzureAppConfigurationClient"
    ) as MockClient:
        yield MockClient


@pytest.fixture
def mock_credential():
    with patch(
        "app.libs.app_configuration.helper.DefaultAzureCredential"
    ) as MockCredential:
        yield MockCredential


def test_initialize_client(mock_app_config_client, mock_credential):
    app_config_endpoint = "https://example-config.azconfig.io"
    helper = AppConfigurationHelper(app_config_endpoint)

    assert helper.app_config_endpoint == app_config_endpoint
    assert helper.credential is not None
    assert helper.app_config_client is not None


def test_initialize_client_no_endpoint(mock_credential):
    with pytest.raises(ValueError, match="App Configuration Endpoint is not set."):
        AppConfigurationHelper(None)


def test_read_configuration(mock_app_config_client, mock_credential):
    app_config_endpoint = "https://example-config.azconfig.io"
    helper = AppConfigurationHelper(app_config_endpoint)

    mock_client_instance = mock_app_config_client.return_value
    mock_client_instance.list_configuration_settings.return_value = [
        ConfigurationSetting(key="test_key", value="test_value")
    ]

    config_settings = helper.read_configuration()
    assert len(config_settings) == 1
    assert config_settings[0].key == "test_key"
    assert config_settings[0].value == "test_value"


def test_read_and_set_environmental_variables(mock_app_config_client, mock_credential):
    app_config_endpoint = "https://example-config.azconfig.io"
    helper = AppConfigurationHelper(app_config_endpoint)

    mock_client_instance = mock_app_config_client.return_value
    mock_client_instance.list_configuration_settings.return_value = [
        ConfigurationSetting(key="test_key", value="test_value")
    ]

    env_vars = helper.read_and_set_environmental_variables()
    assert os.environ["test_key"] == "test_value"
    assert env_vars["test_key"] == "test_value"
