# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Bridge between Azure App Configuration and the local environment.

At application bootstrap the ``AppConfigurationHelper`` connects to an
Azure App Configuration store, enumerates every key-value pair, and
writes each one into ``os.environ``.  This makes the values available to
the Pydantic ``BaseSettings``-based ``Configuration`` class, which reads
from the environment on construction.

Typical bootstrap sequence::

    from libs.azure.app_configuration import AppConfigurationHelper

    helper = AppConfigurationHelper(endpoint_url, credential)
    helper.read_and_set_environmental_variables()

    # Now Configuration() will pick up the App Config values
    config = Configuration()
"""

import os

from azure.appconfiguration import AzureAppConfigurationClient
from azure.identity import (
    AzureCliCredential,
    AzureDeveloperCliCredential,
    DefaultAzureCredential,
    ManagedIdentityCredential,
)

#: Union of all Azure credential types accepted by this module.
AzureCredential = (
    DefaultAzureCredential
    | AzureCliCredential
    | AzureDeveloperCliCredential
    | ManagedIdentityCredential
)


class AppConfigurationHelper:
    """
    Thin wrapper around ``AzureAppConfigurationClient``.

    Responsibilities:
        1. Authenticate to Azure App Configuration using any supported
           credential type (managed identity, CLI, developer CLI, etc.).
        2. Enumerate all key-value pairs stored in the configuration store.
        3. Inject those pairs into ``os.environ`` so downstream Pydantic
           settings classes can read them without any Azure SDK dependency.

    Attributes:
        credential (AzureCredential):
            Azure credential used for authentication.  Defaults to
            ``DefaultAzureCredential`` when none is supplied.
        app_config_endpoint (str | None):
            HTTPS endpoint of the App Configuration store
            (e.g. ``https://<name>.azconfig.io``).
        app_config_client (AzureAppConfigurationClient | None):
            SDK client created during ``__init__``; ``None`` only if
            initialisation has not yet completed.
    """

    credential: AzureCredential | None = None
    app_config_endpoint: str | None = None
    app_config_client: AzureAppConfigurationClient | None = None

    def __init__(
        self, app_configuration_url: str, credential: AzureCredential | None = None
    ):
        """
        Create the helper and connect to the App Configuration store.

        Steps:
            1. Fall back to ``DefaultAzureCredential`` if *credential* is ``None``.
            2. Store the endpoint URL.
            3. Call ``_initialize_client`` to build the SDK client (validates
               that both endpoint and credential are set).

        Args:
            app_configuration_url:
                HTTPS endpoint of the Azure App Configuration resource.
            credential:
                Optional Azure credential.  When omitted the ambient
                ``DefaultAzureCredential`` chain is used, which supports
                managed identity, Azure CLI, environment variables, etc.

        Raises:
            ValueError: If *app_configuration_url* is ``None`` or the
                credential is missing after defaulting.
        """
        self.credential = credential or DefaultAzureCredential()
        self.app_config_endpoint = app_configuration_url
        self._initialize_client()

    def _initialize_client(self):
        """
        Validate prerequisites and construct the SDK client.

        Raises:
            ValueError: If ``app_config_endpoint`` or ``credential`` is
                ``None`` at the point of invocation.
        """
        if self.app_config_endpoint is None:
            raise ValueError("App Configuration Endpoint is not set.")
        if self.credential is None:
            raise ValueError("Azure credential is not set.")

        # The SDK incorrectly derives the credential scope from the endpoint URL
        # (e.g. "https://<name>.azconfig.io/.default") instead of using the
        # canonical audience "https://azconfig.io/.default", which causes a 403
        # when authenticating via Entra ID.  Override it explicitly.
        self.app_config_client = AzureAppConfigurationClient(
            self.app_config_endpoint,
            self.credential,
            credential_scopes=["https://azconfig.io/.default"],
        )

    def read_configuration(self):
        """
        Retrieve every key-value pair from the App Configuration store.

        Returns:
            Iterable[ConfigurationSetting]:
                Paginated iterator of ``ConfigurationSetting`` objects.
                Each item exposes ``.key`` and ``.value`` attributes.

        Raises:
            ValueError: If the SDK client has not been initialised.
        """
        if self.app_config_client is None:
            raise ValueError("App Configuration client is not initialized.")
        return self.app_config_client.list_configuration_settings()

    def read_and_set_environmental_variables(self):
        """
        Pull all settings from App Configuration into ``os.environ``.

        Processing steps:
            1. Call ``read_configuration`` to enumerate every key-value pair.
            2. For each setting, write ``os.environ[key] = value``.
            3. Return the full ``os.environ`` mapping so the caller can
               inspect the merged result if needed.

        Returns:
            os._Environ: The process-wide environment after injection.

        Raises:
            ValueError: Propagated from ``read_configuration`` if the
                client is not initialised.
        """
        configuration_settings = self.read_configuration()
        for item in configuration_settings:
            os.environ[item.key] = item.value

        return os.environ
