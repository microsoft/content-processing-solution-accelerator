# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Minimal environment-variable loader for the App Configuration endpoint.

Read by the application bootstrap before Azure App Configuration is available.
"""

from pydantic import Field

from libs.base.application_models import ModelBaseSettings


class EnvConfiguration(ModelBaseSettings):
    """Loads the App Configuration endpoint from environment / .env.

    Attributes:
        app_config_endpoint: Azure App Configuration endpoint URL.
    """

    app_config_endpoint: str = Field(default="https://example.com")
