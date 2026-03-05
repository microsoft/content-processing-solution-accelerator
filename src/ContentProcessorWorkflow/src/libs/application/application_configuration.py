# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Pydantic-based configuration hierarchy for the Content Processing workflow.

This module defines a three-tier settings model that merges values from
multiple sources in priority order:

    1. Explicit environment variables (highest priority)
    2. ``.env`` file entries
    3. Azure App Configuration keys (fetched at bootstrap)
    4. Field defaults coded here (lowest priority)

Architecture::

    _configuration_base          ← SettingsConfigDict (.env + env vars)
        ├─ _envConfiguration     ← bootstrap-only: APP_CONFIG_ENDPOINT
        └─ Configuration         ← all runtime settings used by the app

``_envConfiguration`` exists solely to discover the Azure App Configuration
endpoint *before* the full ``Configuration`` object is hydrated.  Once the
endpoint is known, the bootstrap layer pulls remaining keys from App Config
and re-loads ``Configuration`` with the merged values.

Naming convention:
    Every ``Configuration`` field maps bi-directionally to an environment
    variable using the rule ``UPPER_CASE_WITH_UNDERSCORES <-> lower_case``.
    Fields that accept legacy or alternate names use the ``alias`` parameter
    so that *either* spelling works at deploy time.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class _configuration_base(BaseSettings):
    """
    Abstract base for all configuration tiers.

    Inherits from ``pydantic_settings.BaseSettings`` to gain automatic
    environment-variable binding, ``.env``-file loading, and JSON-schema
    generation.  Subclasses only need to declare typed ``Field`` attributes
    — the base takes care of discovery and validation.

    Model behaviour:
        * Reads from ``.env`` (UTF-8) when present.
        * Ignores unknown keys (``extra="ignore"``), so the same ``.env``
          file can be shared across multiple configuration tiers without
          triggering validation errors.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class _envConfiguration(_configuration_base):
    """
    Bootstrap-only configuration for locating Azure App Configuration.

    This tiny subclass reads exactly one setting — the App Configuration
    endpoint URL — so the bootstrap layer can connect and pull the remaining
    keys.  It is *not* used at runtime; ``Configuration`` takes over once
    the full key set has been merged.

    Alias handling:
        Historically the variable was named ``APP_CONFIG_ENDPOINT``, but older
        deployment manifests may still use that spelling.  The ``alias``
        parameter ensures both names are accepted transparently, avoiding
        misconfiguration in Azure Container Apps and similar environments.
    """

    # Azure App Configuration endpoint.
    # Historically this project referred to it as APP_CONFIG_ENDPOINT, while the
    # code used APP_CONFIGURATION_URL. Accept both to avoid misconfiguration in
    # deployment environments like Azure Container Apps.
    app_config_endpoint: str | None = Field(
        default=None,
        alias="APP_CONFIG_ENDPOINT",
    )


class Configuration(_configuration_base):
    """
    Runtime configuration for the Content Processing workflow.

    Every field declared here becomes a first-class, type-checked setting
    that is automatically resolved from environment variables, ``.env``
    entries, or Azure App Configuration keys — in that priority order.

    Adding a new setting:
        1. Declare a typed class attribute with a ``Field(default=…)`` value.
        2. Use ``alias="ENV_VAR_NAME"`` if the environment variable name
           differs from the auto-derived ``UPPER_CASE`` form.
        3. Deploy the matching variable in your ``.env``, container-app
           manifest, or App Configuration store.

    Attribute groups:
        Logging
            ``app_logging_enable``, ``app_logging_level`` — control the
            application-wide Python logging configuration.
        Cosmos DB
            ``app_cosmos_connstr``, ``app_cosmos_database``,
            ``app_cosmos_container_batch_process`` — connection and
            container details for the process-state store.
        Storage / Queues
            ``storage_queue_account``, ``storage_queue_name``,
            ``storage_account_process_queue`` — Azure Storage Queue
            identifiers used by ``QueueService``.
        Content Processing
            ``app_cps_content_process_endpoint``,
            ``app_cps_poll_interval_seconds`` — HTTP endpoint and timing
            for the downstream content-processing API.
    """

    # Application Logging Configuration
    app_logging_enable: bool = Field(
        default=False, description="Enable application logging"
    )
    app_logging_level: str = Field(
        default="DEBUG", description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )

    # Sample Configuration
    app_sample_variable: str = Field(
        default="Hello World!", description="Sample configuration variable"
    )
    app_cosmos_connstr: str = Field(
        default="mongodb://<cosmosdb-connection-string>", alias="APP_COSMOS_CONNSTR"
    )
    app_cosmos_database: str = Field(
        default="content-processing-db", alias="APP_COSMOS_DATABASE"
    )
    app_cosmos_container_batch_process: str = Field(
        default="batch-processes", alias="APP_COSMOS_CONTAINER_BATCH_PROCESS"
    )
    storage_queue_account: str = Field(
        default="http://<storage queue url>", alias="STORAGE_QUEUE_ACCOUNT"
    )
    storage_account_process_queue: str = Field(
        default="http://<storage account process queue url>",
        alias="STORAGE_ACCOUNT_PROCESS_QUEUE",
    )
    storage_queue_name: str = Field(
        default="processes-queue", alias="STORAGE_QUEUE_NAME"
    )
    app_storage_account_name: str = Field(
        default="<storage account name>", alias="APP_STORAGE_ACCOUNT_NAME"
    )
    app_cps_process_batch: str = Field(
        default="cps-process-batch", alias="APP_CPS_PROCESS_BATCH"
    )
    app_cps_processes: str = Field(default="cps-processes", alias="APP_CPS_PROCESSES")

    app_cps_content_process_endpoint: str = Field(
        default="http://localhost:8000/", alias="APP_CPS_CONTENT_PROCESS_ENDPOINT"
    )

    app_cps_poll_interval_seconds: float = Field(
        default=3.0,
        alias="APP_CPS_POLL_INTERVAL_SECONDS",
        description="Polling interval (seconds) used when Retry-After is not present",
    )
    app_rai_enabled: bool = Field(
        default=True,
        alias="APP_RAI_ENABLED",
        description="Enable Responsible AI (RAI) analysis in the workflow",
    )

    # Add your custom configuration here:
    # Example configurations (uncomment and modify as needed):

    # Database Configuration
    # database_url: str = Field(default="sqlite:///app.db", description="Database connection URL")
    # database_pool_size: int = Field(default=5, description="Database connection pool size")

    # API Configuration
    # api_timeout: int = Field(default=30, description="API request timeout in seconds")
    # api_retry_attempts: int = Field(default=3, description="Number of API retry attempts")

    # Feature Flags
    # enable_debug_mode: bool = Field(default=False, description="Enable debug mode")
    # enable_feature_x: bool = Field(default=False, description="Enable feature X")

    # Security Configuration
    # secret_key: str = Field(default="change-me-in-production", description="Secret key for encryption")
    # jwt_expiration_hours: int = Field(default=24, description="JWT token expiration in hours")
