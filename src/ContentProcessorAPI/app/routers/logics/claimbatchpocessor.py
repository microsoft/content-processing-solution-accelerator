# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Claim-batch processing logic: manifest CRUD, blob storage, and queue dispatch."""

import json
import uuid
from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field
from sas.cosmosdb.mongo.repository import RepositoryBase, SortField

from app.libs.application.application_configuration import AppConfiguration
from app.libs.application.application_context import AppContext
from app.libs.azure.storage_blob.helper import StorageBlobHelper
from app.libs.azure.storage_queue.helper import StorageQueueHelper
from app.routers.models.contentprocessor.claim_process import (
    Claim_Process,
)
from app.routers.models.contentprocessor.model import ClaimProcessRequest

from ..models.contentprocessor.claim import ClaimItem, ClaimProcess


class ClaimBatchProcessRepository(RepositoryBase[Claim_Process, str]):
    """Cosmos DB repository for claim-process records with pagination support."""

    def __init__(
        self, connection_string: str, database_name: str, collection_name: str
    ):
        super().__init__(
            connection_string=connection_string,
            database_name=database_name,
            collection_name=collection_name,
            indexes=[
                "id",
                "process_name",
                "process_time",
            ],
        )

    async def find_with_pagination_async(
        self,
        predicate: Dict[str, Any],
        sort_fields: List[SortField] = None,
        skip: int = 0,
        limit: int = 100,
        projection: Dict[str, Any] = None,
    ) -> List[BaseModel]:
        """Query the collection with server-side paging and optional projection."""

        await self._ensure_collection_is_ready()

        cursor = (
            self.collection
            .find(predicate, projection)
            .skip(skip)
            .limit(limit)
            .sort(
                [(field.field_name, field.order) for field in sort_fields]
                if sort_fields
                else []
            )
        )
        return await self._cursor_to_entities(cursor)


class ClaimBatchProcessor(BaseModel):
    """Batch-oriented helper for storing per-batch artifacts in Azure Blob Storage.

    Current implementation uses a single configured container/prefix (`app_cps_process_batch`) and
    stores each batch under its `batch_id` as a virtual directory.

    Layout:
    - `{batch_id}/manifest.json` : JSON serialization of `ClaimProcess`
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

    def create_claim_container(self, schemaset_id: str) -> ClaimProcess:
        """Create a new claim manifest and persist it to `{claim_id}/manifest.json`.

        Args:
            schemaset_id: Schema collection ID to associate with the claim.
        Returns:
            The created `ClaimProcess` (also persisted to storage).
        """
        new_claim_id = str(uuid.uuid4())
        claim_process = ClaimProcess(
            claim_id=new_claim_id, schema_collection_id=schemaset_id
        )
        claim_process_manifest_file_name = "manifest.json"
        claim_process_manifest = json.dumps(claim_process.model_dump(mode="json"))
        self._save_manifest_to_blob(
            claim_process_manifest, claim_process_manifest_file_name, new_claim_id
        )

        return claim_process

    def get_claim_manifest(self, claim_id: str) -> ClaimProcess:
        """Load and parse `{claim_id}/manifest.json` into a `ClaimProcess`."""
        claim_process_manifest_file_name = "manifest.json"
        manifest_content = self.blobHelper.download_blob(
            claim_process_manifest_file_name, claim_id
        )
        manifest_dict = json.loads(manifest_content)
        claim_process = ClaimProcess(**manifest_dict)
        return claim_process

    def add_claim_item(self, claim_id: str, claim_item: ClaimItem):
        """Append a new `ClaimItem` to the claim manifest and re-save it.

        Note: assigns a new UUID into `claim_item.id` before persisting.
        """
        claim_process = self.get_claim_manifest(claim_id=claim_id)

        claim_item.id = str(uuid.uuid4())
        claim_process.items.append(claim_item)
        claim_process_manifest_file_name = "manifest.json"
        claim_process_manifest = json.dumps(claim_process.model_dump(mode="json"))
        self._save_manifest_to_blob(
            claim_process_manifest, claim_process_manifest_file_name, claim_id
        )

        return claim_process

    def add_file_to_claim(self, claim_id: str, file_name: str, file_content: bytes):
        """Upload a file blob under the claim prefix (`{claim_id}/{file_name}`)."""
        self.blobHelper.upload_blob(file_name, file_content, claim_id)

    def delete_claim_container(self, claim_id: str):
        """Delete the claim manifest and attempt to clean up the claim prefix."""
        self.blobHelper.delete_folder(folder_name=claim_id)

    def _save_manifest_to_blob(self, content: str, file_name: str, claim_id: str):
        """Persist a manifest file under the claim prefix (`{claim_id}/{file_name}`)."""
        self.blobHelper.upload_blob(file_name, content, claim_id)

    def enqueue_claim_request_for_processing(
        self, claim_process_request: ClaimProcessRequest
    ):
        """Enqueue a message to the claim processing queue for the given claim ID."""
        self.queueHelper.drop_message(claim_process_request)
