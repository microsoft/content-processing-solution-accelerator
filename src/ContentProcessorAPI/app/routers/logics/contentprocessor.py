# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Content-processor logic: blob persistence and queue dispatch."""

from pydantic import BaseModel, ConfigDict, Field

from app.libs.application.application_configuration import (
    AppConfiguration,
)
from app.libs.application.application_context import AppContext
from app.libs.azure.storage_blob.helper import StorageBlobHelper
from app.libs.azure.storage_queue.helper import StorageQueueHelper


class ContentProcessor(BaseModel):
    """Thin wrapper around blob and queue helpers for single-file processing."""

    config: AppConfiguration = Field(default=None)
    blobHelper: StorageBlobHelper = Field(default=None)
    queueHelper: StorageQueueHelper = Field(default=None)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, app_context: AppContext = None):
        super().__init__()
        self.config = app_context.configuration
        self.blobHelper = StorageBlobHelper(
            self.config.app_storage_blob_url, self.config.app_cps_processes
        )
        self.queueHelper = StorageQueueHelper(
            self.config.app_storage_queue_url, self.config.app_message_queue_extract
        )

    def save_file_to_blob(self, process_id: str, file: bytes, file_name: str):
        """Upload the submitted file into blob storage under *process_id*."""
        self.blobHelper.upload_blob(file_name, file, process_id)

    def enqueue_message(self, message_object: BaseModel):
        """Serialize *message_object* and enqueue it for downstream processing."""
        self.queueHelper.drop_message(message_object)
