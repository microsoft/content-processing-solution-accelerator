# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Pydantic settings models for environment and Azure App Configuration.

Defines the two-stage configuration loading used at startup: EnvConfiguration
reads the App Configuration endpoint from environment variables, then
AppConfiguration is populated from the key-values stored in that service.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelBaseSettings(BaseSettings):
    """Base settings class that ignores unknown fields and is case-insensitive."""

    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)


class EnvConfiguration(ModelBaseSettings):
    """Minimal settings read from process environment at startup.

    Attributes:
        app_config_endpoint: Azure App Configuration endpoint URL.
    """

    app_config_endpoint: str = Field(alias="APP_CONFIG_ENDPOINT")


class AppConfiguration(ModelBaseSettings):
    """Full application settings pulled from Azure App Configuration.

    Attributes:
        app_storage_blob_url: Azure Blob Storage account URL.
        app_storage_queue_url: Azure Queue Storage account URL.
        app_cosmos_connstr: Cosmos DB connection string.
        app_cosmos_database: Cosmos DB database name.
        app_cosmos_container_schema: Cosmos DB container for schemas.
        app_cosmos_container_schemaset: Cosmos DB container for schema sets.
        app_cosmos_container_process: Cosmos DB container for processes.
        app_cosmos_container_batches: Cosmos DB container for batches.
        app_cps_configuration: Content-processing pipeline configuration key.
        app_cps_processes: Content-processing pipeline processes key.
        app_cps_process_batch: Content-processing batch queue name.
        app_message_queue_extract: Extraction message-queue name.
        app_cps_max_filesize_mb: Maximum upload file size in megabytes.
        app_logging_level: Application log level.
        azure_package_logging_level: Log level for Azure SDK packages.
        azure_logging_packages: Comma-separated Azure package logger names.
    """

    app_storage_blob_url: str
    app_storage_queue_url: str
    app_cosmos_connstr: str
    app_cosmos_database: str
    app_cosmos_container_schema: str
    app_cosmos_container_schemaset: str
    app_cosmos_container_process: str
    app_cosmos_container_batches: str = "batches"
    app_cps_configuration: str
    app_cps_processes: str
    app_cps_process_batch: str = "process-batch"
    app_message_queue_extract: str
    app_cps_max_filesize_mb: int
    app_logging_level: str
    azure_package_logging_level: str
    azure_logging_packages: str
    applicationinsights_connection_string: str = ""
