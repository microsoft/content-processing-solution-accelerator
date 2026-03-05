# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Azure service helpers used by the Content Processing workflow.

Modules:
    app_configuration
        ``AppConfigurationHelper`` -- thin wrapper around the
        ``AzureAppConfigurationClient`` that reads all key-value pairs
        from an Azure App Configuration store and injects them into
        ``os.environ`` so they become available to the Pydantic-based
        ``Configuration`` hierarchy at bootstrap time.
"""
