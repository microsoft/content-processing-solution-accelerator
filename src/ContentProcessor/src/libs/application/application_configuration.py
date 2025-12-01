# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from pydantic import field_validator
from pydantic_settings import NoDecode
from typing_extensions import Annotated

from libs.base.application_models import ModelBaseSettings


class AppConfiguration(ModelBaseSettings):
    """
    This is Application Configuration Model.
    Which is used to store application configuration settings from environment variables.
    This object will be used to store the configuration settings of the application.
    Attributes:
        app_storage_queue_url (str): The URL of the Azure Storage Queue.
        app_storage_blob_url (str): The URL of the Azure Storage Blob.
        app_process_steps (list[str]): The list of process steps to be executed.
        app_message_queue_interval (int): The interval for the message queue.
        app_message_queue_visibility_timeout (int): The visibility timeout for the message queue.
        app_message_queue_process_timeout (int): The process timeout for the message queue.
        app_logging_level (str): The logging level to be used.
        azure_package_logging_level (str): The logging level for Azure packages.
        azure_logging_packages (str): The list of Azure logging packages.
        app_cps_processes (str): Folder name CPS processes name in Blob Container.
        app_cps_configuration (str): Folder CPS configuration name Blob Container.
        app_content_understanding_endpoint (str): The endpoint for content understanding Service.
        app_ai_project_endpoint (str): The AI Foundry project endpoint.
        app_azure_openai_endpoint (str): The endpoint for Azure OpenAI.
        app_azure_openai_model (str): The model for Azure OpenAI.
        app_cosmos_connstr (str): The connection string for Cosmos DB.
        app_cosmos_database (str): The name of the Cosmos DB database.
        app_cosmos_container_process (str): The name of the Cosmos DB container for process data.
        app_cosmos_container_schema (str): The name of the Cosmos DB container for schema data.
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
