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
    app_logging_enable: bool
    app_logging_level: str


# Read .env file
# Get Current Path + .env file
env_file_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_file_path)

# Get App Configuration
env_config = EnvConfiguration()
app_helper = AppConfigurationHelper(env_config.app_config_endpoint)
app_helper.read_and_set_environmental_variables()

app_config = AppConfiguration()

if app_config.app_logging_enable:
    # Read Configuration for Logging Level as a Text then retrive the logging level
    logging_level = getattr(
        logging, app_config.app_logging_level
    )
    logging.basicConfig(level=logging_level)
else:
    logging.disable(logging.CRITICAL)


# Dependency Function
def get_app_config() -> AppConfiguration:
    return app_config
