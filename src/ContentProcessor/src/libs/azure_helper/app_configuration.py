# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import os

from azure.appconfiguration import AzureAppConfigurationClient
from helpers.azure_credential_utils import get_azure_credential


class AppConfigurationHelper:
    app_config_endpoint: str = None
    app_config_client: AzureAppConfigurationClient = None

    def __init__(self, app_config_endpoint: str):
        self.credential = get_azure_credential()
        self.app_config_endpoint = app_config_endpoint
        self._initialize_client()

    def _initialize_client(self):
        if self.app_config_endpoint is None:
            raise ValueError("App Configuration Endpoint is not set.")

        self.app_config_client = AzureAppConfigurationClient(
            self.app_config_endpoint, self.credential
        )

    def read_configuration(self):
        return self.app_config_client.list_configuration_settings()

    def read_and_set_environmental_variables(self):
        for item in self.read_configuration():
            os.environ[item.key] = item.value
        return os.environ
