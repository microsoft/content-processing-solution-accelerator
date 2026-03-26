# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Direct resource access service for content processing.

Replaces HTTP calls to ContentProcessorAPI with direct Azure resource
operations (Cosmos DB, Blob Storage, Storage Queue).  This eliminates
the dependency on the API's HTTP endpoint from the Workflow, avoiding
Easy Auth sidecar issues for internal service-to-service traffic.
"""

import asyncio
import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from azure.identity import DefaultAzureCredential
from azure.storage.queue import QueueClient
from sas.cosmosdb.mongo.repository import RepositoryBase
from sas.storage import StorageBlobHelper

from libs.application.application_configuration import Configuration

from .content_process_models import (
    ArtifactType,
    ContentProcessMessage,
    ContentProcessRecord,
    PipelineStatus,
    PipelineStep,
    ProcessFile,
)

logger = logging.getLogger(__name__)


class _ProcessRepository(RepositoryBase[ContentProcessRecord, str]):
    """Thin repository for the Processes Cosmos collection."""

    def __init__(self, connection_string: str, database_name: str, container_name: str):
        super().__init__(
            connection_string,
            database_name,
            container_name,
            indexes=["id", "process_id"],
        )


class ContentProcessService:
    """Direct resource access to content processing — replaces HTTP calls to API.

    Uses ``sas-cosmosdb`` (RepositoryBase) for Cosmos DB operations,
    ``sas-storage`` (StorageBlobHelper) for blob operations, and native
    Azure SDK for queue operations.

    Provides four operations matching the API endpoints the Workflow previously
    called over HTTP:
        - submit: upload blob + enqueue + cosmos insert
        - get_status: query Cosmos for process status
        - get_processed: query Cosmos for full processed result
        - get_steps: download step_outputs.json from blob
    """

    def __init__(self, config: Configuration, credential: DefaultAzureCredential):
        self._config = config
        self._credential = credential

        # Cosmos DB via sas-cosmosdb
        self._process_repo = _ProcessRepository(
            connection_string=config.app_cosmos_connstr,
            database_name=config.app_cosmos_database,
            container_name=config.app_cosmos_container_process,
        )

        # Blob Storage via sas-storage — lazy-init on first use
        self._blob_helper: StorageBlobHelper | None = None

        # Queue — lazy-init on first use
        self._queue_client: QueueClient | None = None

    def _get_blob_helper(self) -> StorageBlobHelper:
        """Return the sas-storage Blob helper, creating if needed."""
        if self._blob_helper is None:
            self._blob_helper = StorageBlobHelper(
                account_name=self._config.app_storage_account_name,
                credential=self._credential,
            )
        return self._blob_helper

    def _get_queue_client(self) -> QueueClient:
        """Return the Storage Queue client, connecting if needed."""
        if self._queue_client is None:
            self._queue_client = QueueClient(
                account_url=self._config.app_storage_queue_url,
                queue_name=self._config.app_message_queue_extract,
                credential=self._credential,
            )
        return self._queue_client

    async def submit(
        self,
        file_bytes: bytes,
        filename: str,
        mime_type: str,
        schema_id: str,
        metadata_id: str,
    ) -> str:
        """Upload file to blob, enqueue processing message, create Cosmos record.

        Returns the generated process_id.
        """
        process_id = str(uuid.uuid4())

        # 1. Upload file to blob: {cps-processes}/{process_id}/{filename}
        container_name = self._config.app_cps_processes
        blob_helper = self._get_blob_helper()
        await asyncio.to_thread(
            blob_helper.upload_blob,
            container_name=container_name,
            blob_name=f"{process_id}/{filename}",
            data=file_bytes,
        )

        # 2. Insert Cosmos record BEFORE enqueuing — the external
        #    ContentProcessor does find_document({"process_id": ...}) and
        #    only $set-updates the existing doc.  If the doc doesn't exist
        #    yet, it inserts a duplicate without the "id" field, causing
        #    get_status (which queries by "id") to always see "processing".
        record = ContentProcessRecord(
            id=process_id,
            process_id=process_id,
            processed_file_name=filename,
            processed_file_mime_type=mime_type,
            status="processing",
            imported_time=datetime.now(timezone.utc),
        )
        await self._process_repo.add_async(record)

        # 3. Enqueue processing message (after Cosmos record exists)
        message = ContentProcessMessage(
            process_id=process_id,
            files=[
                ProcessFile(
                    process_id=process_id,
                    id=str(uuid.uuid4()),
                    name=filename,
                    size=len(file_bytes),
                    mime_type=mime_type,
                    artifact_type=ArtifactType.SourceContent,
                    processed_by="Workflow",
                )
            ],
            pipeline_status=PipelineStatus(
                process_id=process_id,
                schema_id=schema_id,
                metadata_id=metadata_id,
                creation_time=datetime.now(timezone.utc),
                steps=[
                    PipelineStep.Extract.value,
                    PipelineStep.Mapping.value,
                    PipelineStep.Evaluating.value,
                    PipelineStep.Save.value,
                ],
                remaining_steps=[
                    PipelineStep.Extract.value,
                    PipelineStep.Mapping.value,
                    PipelineStep.Evaluating.value,
                    PipelineStep.Save.value,
                ],
                completed_steps=[],
            ),
        )
        await asyncio.to_thread(
            self._get_queue_client().send_message,
            message.model_dump_json(),
        )

        logger.info("Submitted process %s for file %s", process_id, filename)
        return process_id

    async def get_status(self, process_id: str) -> dict | None:
        """Query Cosmos for process status.

        Returns a dict with keys: status, process_id, file_name.
        Returns None if not found.
        """
        record = await self._process_repo.get_async(process_id)
        if record is None:
            return None
        return {
            "status": getattr(record, "status", "processing") or "processing",
            "process_id": process_id,
            "file_name": getattr(record, "processed_file_name", "") or "",
        }

    async def get_processed(self, process_id: str) -> dict | None:
        """Query Cosmos for the full processed content result.

        Returns the full document dict, or None if not found.
        """
        record = await self._process_repo.get_async(process_id)
        if record is None:
            return None
        return record.model_dump()

    def get_steps(self, process_id: str) -> list | None:
        """Download step_outputs.json from blob storage.

        Returns parsed list of step output dicts, or None if not found.
        """
        container_name = self._config.app_cps_processes
        blob_name = f"{process_id}/step_outputs.json"
        try:
            blob_helper = self._get_blob_helper()
            data = blob_helper.download_blob(
                container_name=container_name,
                blob_name=blob_name,
            )
            return json.loads(data.decode("utf-8"))
        except Exception:
            logger.debug("step_outputs.json not found for process %s", process_id)
            return None

    async def poll_status(
        self,
        process_id: str,
        poll_interval_seconds: float = 5.0,
        timeout_seconds: float = 600.0,
        on_status_change: Callable[[str, dict], Awaitable[None]] | None = None,
    ) -> dict:
        """Poll Cosmos for status until terminal state or timeout.

        Args:
            on_status_change: Optional async callback invoked whenever the
                status value changes between polls.  Receives
                ``(new_status, result_dict)``.

        Returns the final status dict with keys: status, process_id, file_name.
        """
        elapsed = 0.0
        last_status: str | None = None
        result: dict | None = None
        while elapsed < timeout_seconds:
            result = await self.get_status(process_id)
            if result is None:
                return {
                    "status": "Failed",
                    "process_id": process_id,
                    "file_name": "",
                    "terminal": True,
                }

            status = result.get("status", "processing")

            if status != last_status:
                logger.info(
                    "Poll status change: process_id=%s %s -> %s",
                    process_id,
                    last_status,
                    status,
                )
                last_status = status
                if on_status_change is not None:
                    await on_status_change(status, result)

            if status in ("Completed", "Error"):
                result["terminal"] = True
                return result

            await asyncio.sleep(poll_interval_seconds)
            elapsed += poll_interval_seconds

        # Timeout
        return {
            "status": result.get("status", "processing") if result else "Timeout",
            "process_id": process_id,
            "file_name": result.get("file_name", "") if result else "",
            "terminal": True,
        }

    def close(self):
        """Release connections."""
        self._blob_helper = None
        if self._queue_client is not None:
            self._queue_client.close()
            self._queue_client = None
