# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import logging
import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.libs.app_configuration.helper import AppConfigurationHelper


class ModelBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)


class EnvConfiguration(ModelBaseSettings):
    app_config_endpoint: str


class AppConfiguration(ModelBaseSettings):
    app_storage_blob_url: str
    app_storage_queue_url: str
    app_cosmos_connstr: str
    app_cosmos_database: str
    app_cosmos_container_schema: str
    app_cosmos_container_process: str
    app_cps_configuration: str
    app_cps_processes: str
    app_message_queue_extract: str
    app_cps_max_filesize_mb: int
    app_logging_level: str
    azure_package_logging_level: str
    azure_logging_packages: str


# Read .env file
# Get Current Path + .env file
env_file_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_file_path)

# Get App Configuration
env_config = EnvConfiguration()
app_helper = AppConfigurationHelper(env_config.app_config_endpoint)
app_helper.read_and_set_environmental_variables()

app_config = AppConfiguration()

# Configure logging
# Basic application logging (default: INFO level)
AZURE_BASIC_LOGGING_LEVEL = app_config.app_logging_level.upper()
# Azure package logging (default: WARNING level to suppress INFO)
AZURE_PACKAGE_LOGGING_LEVEL = app_config.azure_package_logging_level.upper()
AZURE_LOGGING_PACKAGES = (
    app_config.azure_logging_packages.split(",") if app_config.azure_logging_packages else []
)

# Basic config: logging.basicConfig with formatted output
logging.basicConfig(
    level=getattr(logging, AZURE_BASIC_LOGGING_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Package config: Azure loggers set to WARNING to suppress INFO
for logger_name in AZURE_LOGGING_PACKAGES:
    logging.getLogger(logger_name).setLevel(
        getattr(logging, AZURE_PACKAGE_LOGGING_LEVEL, logging.WARNING)
    )


# Dependency Function
def get_app_config() -> AppConfiguration:
    return app_config
