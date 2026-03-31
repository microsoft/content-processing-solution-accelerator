# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Wrapper around AzureAppConfigurationClient for bootstrap config loading.

Used by Application_Base at startup to pull all key-values from Azure App
Configuration and inject them into the process environment before Pydantic
settings models are instantiated.
"""

import os

from azure.appconfiguration import AzureAppConfigurationClient

from app.utils.azure_credential_utils import get_azure_credential


class AppConfigurationHelper:
    """Read Azure App Configuration key-values and export them as env vars.

    Responsibilities:
        1. Authenticate to Azure App Configuration via DefaultAzureCredential.
        2. List all configuration settings and set each as an OS environment variable.

    Attributes:
        app_config_endpoint: The App Configuration service URL.
        app_config_client: Authenticated SDK client.
    """

    app_config_endpoint: str = None
    app_config_client: AzureAppConfigurationClient = None

    def __init__(self, app_config_endpoint: str):
        """Create a helper bound to *app_config_endpoint*.

        Args:
            app_config_endpoint: URL of the Azure App Configuration instance.
        """
        self.credential = get_azure_credential()
        self.app_config_endpoint = app_config_endpoint
        self._initialize_client()

    def _initialize_client(self):
        """Create the SDK client; raises if no endpoint was provided."""
        if self.app_config_endpoint is None:
            raise ValueError("App Configuration Endpoint is not set.")

        # The SDK incorrectly derives the credential scope from the endpoint URL
        # instead of using the canonical audience "https://azconfig.io/.default",
        # which causes a 403 when authenticating via Entra ID.
        self.app_config_client = AzureAppConfigurationClient(
            self.app_config_endpoint,
            self.credential,
            credential_scopes=["https://azconfig.io/.default"],
        )

    def read_configuration(self):
        """Return an iterator of all configuration settings from the service."""
        return self.app_config_client.list_configuration_settings()

    def read_and_set_environmental_variables(self):
        """Fetch all settings and write each key-value pair into ``os.environ``.

        Returns:
            The updated ``os.environ`` mapping.
        """
        for item in self.read_configuration():
            os.environ[item.key] = item.value
        return os.environ
