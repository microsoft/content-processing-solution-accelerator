# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Claim-batch processing logic: manifest CRUD, blob storage, and queue dispatch."""

import json
import uuid

from pydantic import BaseModel, ConfigDict, Field
from sas.cosmosdb.mongo.repository import RepositoryBase

from app.libs.application.application_configuration import AppConfiguration
from app.libs.application.application_context import AppContext
from app.libs.azure.storage_blob.helper import StorageBlobHelper
from app.libs.azure.storage_queue.helper import StorageQueueHelper
from app.routers.models.contentprocessor.claim_process import Claim_Process
from app.routers.models.contentprocessor.model import ClaimProcessRequest

from ..models.contentprocessor.claim import BatchProcess, ClaimItem


class ClaimBatchProcessRepository(RepositoryBase[Claim_Process, str]):
    """Cosmos DB repository for claim-process records."""

    def __init__(self, connection_string: str, database_name: str, container_name: str):
        super().__init__(
            connection_string=connection_string,
            db_name=database_name,
            container_name=container_name,
            indexes=[
                "id",
                "process_name",
            ],
        )


class ClaimBatchProcessor(BaseModel):
    """Batch-oriented helper for storing per-batch artifacts in Azure Blob Storage.

    Current implementation uses a single configured container/prefix (`app_cps_process_batch`) and
    stores each batch under its `batch_id` as a virtual directory.

    Layout:
    - `{batch_id}/manifest.json` : JSON serialization of `BatchProcess`
    - `{batch_id}/{file_name}`  : user uploaded files for the batch
    """

    config: AppConfiguration = Field(default=None)
    blobHelper: StorageBlobHelper = Field(default=None)
    queueHelper: StorageQueueHelper = Field(default=None)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, app_context: AppContext = None):
        super().__init__()
        self.config = app_context.configuration
        self.blobHelper = StorageBlobHelper(
            self.config.app_storage_blob_url, self.config.app_cps_process_batch
        )
        self.queueHelper = StorageQueueHelper(
            self.config.app_storage_queue_url, "claim-process-queue"
        )

    def create_batch_container(self, schemaset_id: str) -> BatchProcess:
        """Create a new batch manifest and persist it to `{batch_id}/manifest.json`.

        Args:
            schemaset_id: Schema collection ID to associate with the batch.

        Returns:
            The created `BatchProcess` (also persisted to storage).
        """
        new_batch_id = str(uuid.uuid4())
        batch_process = BatchProcess(
            batch_id=new_batch_id, schema_collection_id=schemaset_id
        )
        batch_process_manifest_file_name = "manifest.json"
        batch_process_manifest = json.dumps(batch_process.model_dump(mode="json"))
        self._save_manifest_to_blob(
            batch_process_manifest, batch_process_manifest_file_name, new_batch_id
        )

        return batch_process

    def get_batch_manifest(self, batch_id: str) -> BatchProcess:
        """Load and parse `{batch_id}/manifest.json` into a `BatchProcess`."""
        batch_process_manifest_file_name = "manifest.json"
        manifest_content = self.blobHelper.download_blob(
            batch_process_manifest_file_name, batch_id
        )
        manifest_dict = json.loads(manifest_content)
        batch_process = BatchProcess(**manifest_dict)
        return batch_process

    def add_batch_item(self, batch_id: str, batch_item: ClaimItem):
        """Append a new `BatchItem` to the batch manifest and re-save it.

        Note: assigns a new UUID into `batch_item.id` before persisting.
        """
        batch_process = self.get_batch_manifest(batch_id=batch_id)

        batch_item.id = str(uuid.uuid4())
        batch_process.items.append(batch_item)
        batch_process_manifest_file_name = "manifest.json"
        batch_process_manifest = json.dumps(batch_process.model_dump(mode="json"))
        self._save_manifest_to_blob(
            batch_process_manifest, batch_process_manifest_file_name, batch_id
        )

        return batch_process

    def add_file_to_batch(self, batch_id: str, file_name: str, file_content: bytes):
        """Upload a file blob under the batch prefix (`{batch_id}/{file_name}`)."""
        self.blobHelper.upload_blob(file_name, file_content, batch_id)

    def delete_batch_container(self, batch_id: str):
        """Delete the batch manifest and attempt to clean up the batch prefix."""
        self.blobHelper.delete_folder(folder_name=batch_id)

    def _save_manifest_to_blob(self, content: str, file_name: str, batch_id: str):
        """Persist a manifest file under the batch prefix (`{batch_id}/{file_name}`)."""
        self.blobHelper.upload_blob(file_name, content, batch_id)

    def enqueue_claim_batch_for_processing(
        self, claim_process_request: ClaimProcessRequest
    ):
        """Enqueue a message to the claim processing queue for the given batch ID."""
        message_object = {"batch_process_id": claim_process_request.claim_process_id}
        self.queueHelper.drop_message(message_object)

    async def get_claim_batch_status(self, batch_process_id: str) -> BatchProcess:
        """Retrieve the status of a claim batch by its batch process ID."""
        raise NotImplementedError
