# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Pydantic settings models sourced from Azure App Configuration and .env files.

Defines the typed configuration surface consumed by every pipeline step and
helper class in the Content Processor.
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from typing_extensions import Annotated


class _configuration_base(BaseSettings):
    """Shared Pydantic-settings base that reads from .env files."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class _envConfiguration(_configuration_base):
    """Loads the App Configuration endpoint URL from environment variables.

    Attributes:
        app_configuration_url: Azure App Configuration endpoint.
    """

    app_configuration_url: str | None = Field(default=None)


class AppConfiguration(_configuration_base):
    """Typed application settings populated from Azure App Configuration.

    Attributes:
        app_storage_queue_url: Azure Storage Queue account URL.
        app_storage_blob_url: Azure Storage Blob account URL.
        app_process_steps: Ordered list of pipeline step names.
        app_message_queue_interval: Polling interval in seconds.
        app_message_queue_visibility_timeout: Queue message visibility timeout.
        app_message_queue_process_timeout: Max processing time per message.
        app_logging_level: Application log level (DEBUG, INFO, …).
        azure_package_logging_level: Log level for Azure SDK packages.
        azure_logging_packages: Comma-separated Azure package names to configure.
        app_cps_processes: Blob container folder for CPS process definitions.
        app_cps_configuration: Blob container folder for CPS configuration.
        app_content_understanding_endpoint: Azure Content Understanding endpoint.
        app_ai_project_endpoint: AI Foundry project endpoint.
        app_azure_openai_endpoint: Azure OpenAI endpoint.
        app_azure_openai_model: Azure OpenAI deployment/model name.
        app_cosmos_connstr: Cosmos DB (Mongo API) connection string.
        app_cosmos_database: Cosmos DB database name.
        app_cosmos_container_process: Cosmos DB container for process data.
        app_cosmos_container_schema: Cosmos DB container for schema data.
    """

    app_storage_queue_url: str
    app_storage_blob_url: str
    app_process_steps: Annotated[list[str], NoDecode]
    app_message_queue_interval: int
    app_message_queue_visibility_timeout: int
    app_message_queue_process_timeout: int
    app_logging_level: str
    azure_package_logging_level: str
    azure_logging_packages: str
    app_cps_processes: str
    app_cps_configuration: str
    app_content_understanding_endpoint: str
    app_ai_project_endpoint: str
    app_azure_openai_endpoint: str
    app_azure_openai_model: str
    app_cosmos_connstr: str
    app_cosmos_database: str
    app_cosmos_container_process: str
    app_cosmos_container_schema: str

    @field_validator("app_process_steps", mode="before")
    @classmethod
    def split_processes(cls, v: str) -> list[str]:
        if isinstance(v, str):
            return [x for x in v.split(",")]
        return v
