# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Azure App Configuration client helper.

Reads configuration key-values at startup and optionally projects them
into ``os.environ`` so that Pydantic settings models can pick them up.
"""

import os

from azure.appconfiguration import AzureAppConfigurationClient

from libs.utils.azure_credential_utils import get_azure_credential


class AppConfigurationHelper:
    """Thin wrapper around AzureAppConfigurationClient.

    Responsibilities:
        1. Authenticate to App Configuration with the shared Azure credential.
        2. List all configuration settings.
        3. Optionally push them into environment variables.

    Attributes:
        app_config_endpoint: The App Configuration endpoint URL.
        app_config_client: The underlying SDK client.
    """

    app_config_endpoint: str = None
    app_config_client: AzureAppConfigurationClient = None

    def __init__(self, app_config_endpoint: str):
        self.credential = get_azure_credential()
        self.app_config_endpoint = app_config_endpoint
        self._initialize_client()

    def _initialize_client(self):
        """Create the App Configuration SDK client.

        Raises:
            ValueError: If the endpoint has not been set.
        """
        if self.app_config_endpoint is None:
            raise ValueError("App Configuration Endpoint is not set.")

        self.app_config_client = AzureAppConfigurationClient(
            self.app_config_endpoint, self.credential
        )

    def read_configuration(self):
        """Return an iterator of all configuration settings."""
        return self.app_config_client.list_configuration_settings()

    def read_and_set_environmental_variables(self):
        """Read all settings and project them into ``os.environ``."""
        for item in self.read_configuration():
            os.environ[item.key] = item.value
        return os.environ
