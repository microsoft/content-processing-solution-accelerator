# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Document-processing executor for the claim workflow pipeline.

First step in the three-stage pipeline (document_processing -> summarizing ->
gap_analysis).  Downloads a manifest from blob storage, submits each
referenced file to the content-processing service, polls for completion, and
upserts per-file results into Cosmos DB.

Uses direct resource access (Blob, Queue, Cosmos DB) instead of HTTP calls
to the ContentProcessorAPI, avoiding Easy Auth sidecar issues.
"""

import asyncio
import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path

from agent_framework import Executor, WorkflowContext, handler
from sas.storage.blob.async_helper import AsyncStorageBlobHelper

from libs.application.application_context import AppContext
from repositories.claim_processes import Claim_Process, Claim_Processes, Content_Process
from services.content_process_service import ContentProcessService
from steps.models.output import Executor_Output, Workflow_Output

from ...models.manifest import ClaimProcess


class DocumentProcessExecutor(Executor):
    """Workflow executor that runs the document-processing step.

    Responsibilities:
        1. Generate a unique, lexicographically sortable claim-process name.
        2. Download ``manifest.json`` from the process-batch blob container.
        3. Create a ``Claim_Process`` record in Cosmos DB.
        4. Submit each manifest file directly via blob/queue/cosmos.
        5. Poll Cosmos DB until terminal status and upsert progress.
        6. Forward the aggregated ``Workflow_Output`` to the next executor.

    Class-level Attributes:
        _claim_name_lock: Async lock protecting the timestamp-sequence counter.
        _claim_name_last_ts: Last timestamp string used for name generation.
        _claim_name_seq: Sequence counter for same-timestamp disambiguation.
    """

    _claim_name_lock = asyncio.Lock()
    _claim_name_last_ts: str | None = None
    _claim_name_seq: int = 0

    @classmethod
    async def _generate_claim_process_name(
        cls,
        *,
        claim_id: str,
        created_time: datetime | None = None,
    ) -> str:
        """Create a unique, time-sequential, lexicographically sortable process name.

        Format: Claim-<YYYYMMDDHHMMSSffffff>-<SEQ>-<CLAIM>
        - Time prefix sorts naturally by name.
        - SEQ breaks ties when timestamps repeat.
        - CLAIM adds extra uniqueness without impacting ordering.
        """

        if created_time is not None and not isinstance(created_time, datetime):
            created_time = None

        dt = created_time or datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt = dt.astimezone(timezone.utc)

        ts = dt.strftime("%Y%m%d%H%M%S%f")

        # Protect against same-timestamp collisions (rare but possible).
        async with cls._claim_name_lock:
            if ts == cls._claim_name_last_ts:
                cls._claim_name_seq += 1
            else:
                cls._claim_name_last_ts = ts
                cls._claim_name_seq = 0
            seq = cls._claim_name_seq

        batch_fragment = "".join(ch for ch in str(claim_id) if ch.isalnum())[:6].upper()
        if not batch_fragment:
            batch_fragment = uuid.uuid4().hex[:6].upper()

        return f"claim-{ts}-{seq:04d}-{batch_fragment}"

    def __init__(self, id: str, app_context: AppContext):
        """Create a new document process executor bound to an application context."""
        super().__init__(id=id)
        self.app_context = app_context

    @handler
    async def handle_execute(
        self,
        claim_id: str,
        ctx: WorkflowContext[Workflow_Output],
    ) -> None:
        """Execute document processing for a claim via direct resource access.

        Steps:
            1. Download ``manifest.json`` from the process-batch container.
            2. Generate a unique claim-process name and persist a new
               ``Claim_Process`` record in Cosmos DB.
            3. Submit each manifest file directly to blob/queue/cosmos
               (no HTTP calls to ContentProcessorAPI).
            4. Poll Cosmos DB for each submission until terminal status.
            5. Fetch final output scores and upsert ``Content_Process``
               records.
            6. Aggregate per-file results into a ``Workflow_Output`` and
               forward it to the next executor via the workflow context.

        Args:
            claim_id: Identifier of the claim to process.
            ctx: Workflow context carrying shared state across executors.
        """
        storage_helper = await self.app_context.get_service_async(
            AsyncStorageBlobHelper
        )
        claim_process_repository = self.app_context.get_service(Claim_Processes)
        content_process_service = self.app_context.get_service(ContentProcessService)

        manifest_stream = await storage_helper.download_blob(
            self.app_context.configuration.app_cps_process_batch,
            f"{claim_id}/manifest.json",
        )
        manifest = ClaimProcess.model_validate_json(manifest_stream)

        new_claim_process_name = await self._generate_claim_process_name(
            claim_id=claim_id,
            created_time=getattr(manifest, "created_time", None),
        )

        new_claim_process = Claim_Process(
            id=claim_id,
            process_name=new_claim_process_name,
            schemaset_id=manifest.schema_collection_id,
            metadata_id=manifest.metadata_id,
        )
        await claim_process_repository.Create_Claim_Process(new_claim_process)

        document_results: list[dict] = []

        poll_interval_seconds = float(
            getattr(
                self.app_context.configuration,
                "app_cps_poll_interval_seconds",
                5.0,
            )
        )

        # Limit concurrency to avoid overwhelming the ContentProcessor.
        max_concurrency = 2
        semaphore = asyncio.Semaphore(max_concurrency)

        # Serialize Cosmos upserts on the parent Claim_Process document to
        # prevent concurrent read-modify-write from reverting status updates.
        upsert_lock = asyncio.Lock()

        async def _process_one(item) -> dict:
            async with semaphore:
                content_type, _ = mimetypes.guess_type(str(item.file_name))
                try:
                    source_file = await storage_helper.download_blob(
                        container_name=self.app_context.configuration.app_cps_process_batch,
                        blob_name=f"{claim_id}/{item.file_name}",
                    )

                    filename = Path(str(item.file_name)).name
                    file_bytes = bytes(source_file)

                    metadata_id = (
                        item.metadata_id if item.metadata_id else f"Meta-{uuid.uuid4()}"
                    )
                    schema_id = str(item.schema_id)

                    # Direct submit: blob upload + queue enqueue + cosmos insert
                    process_id = await content_process_service.submit(
                        file_bytes=file_bytes,
                        filename=filename,
                        mime_type=content_type or "application/octet-stream",
                        schema_id=schema_id,
                        metadata_id=metadata_id,
                    )

                    # Upsert initial status to claim process
                    async with upsert_lock:
                        await claim_process_repository.Upsert_Content_Process(
                            process_id=claim_id,
                            content_process=Content_Process(
                                process_id=process_id,
                                file_name=str(item.file_name),
                                mime_type=content_type or "application/octet-stream",
                                status="processing",
                            ),
                        )

                    # Poll Cosmos directly until terminal status,
                    # propagating interim step statuses to the claim process.
                    async def _on_status_change(new_status: str, _result: dict) -> None:
                        async with upsert_lock:
                            await claim_process_repository.Upsert_Content_Process(
                                process_id=claim_id,
                                content_process=Content_Process(
                                    process_id=process_id,
                                    file_name=str(item.file_name),
                                    mime_type=content_type
                                    or "application/octet-stream",
                                    status=new_status,
                                ),
                            )

                    poll_result = await content_process_service.poll_status(
                        process_id=process_id,
                        poll_interval_seconds=poll_interval_seconds,
                        timeout_seconds=600.0,
                        on_status_change=_on_status_change,
                    )

                    status_text = poll_result.get("status", "Failed")

                    # Fetch final processed result for scores
                    schema_score_f = 0.0
                    entity_score_f = 0.0
                    processed_time = ""
                    result_payload = None

                    if process_id:
                        final_payload = await content_process_service.get_processed(
                            process_id
                        )
                        if isinstance(final_payload, dict):
                            status_text = final_payload.get("status") or status_text
                            try:
                                schema_score_f = float(
                                    final_payload.get("schema_score") or 0.0
                                )
                            except Exception:
                                schema_score_f = 0.0
                            try:
                                entity_score_f = float(
                                    final_payload.get("entity_score") or 0.0
                                )
                            except Exception:
                                entity_score_f = 0.0
                            try:
                                processed_time = (
                                    final_payload.get("processed_time") or ""
                                )
                            except Exception:
                                processed_time = ""
                            result_payload = final_payload

                        # Final cosmos upsert with scores
                        async with upsert_lock:
                            await claim_process_repository.Upsert_Content_Process(
                                process_id=claim_id,
                                content_process=Content_Process(
                                    process_id=process_id,
                                    file_name=str(item.file_name),
                                    mime_type=content_type
                                    or "application/octet-stream",
                                    status=status_text,
                                    schema_score=schema_score_f,
                                    entity_score=entity_score_f,
                                    processed_time=processed_time,
                                ),
                            )

                    # Map status to HTTP-like code for downstream compatibility
                    if status_text == "Completed":
                        status_code = 302
                    elif status_text in ("Error", "Failed"):
                        status_code = 500
                    else:
                        status_code = 200

                    return {
                        "file_name": str(item.file_name),
                        "schema_id": str(item.schema_id),
                        "mime_type": content_type or "application/octet-stream",
                        "process_id": process_id,
                        "status": status_code,
                        "final_status": status_text,
                        "schema_score": schema_score_f,
                        "entity_score": entity_score_f,
                        "response": result_payload,
                        "poll_url": "",
                    }
                except Exception as e:
                    return {
                        "file_name": str(getattr(item, "file_name", "<unknown>")),
                        "schema_id": str(getattr(item, "schema_id", "<unknown>")),
                        "status": "exception",
                        "response": f"{type(e).__name__}: {e}",
                    }

        tasks: list[asyncio.Task[dict]] = []
        async with asyncio.TaskGroup() as tg:
            for item in manifest.items:
                tasks.append(tg.create_task(_process_one(item)))

        document_results.extend([t.result() for t in tasks])

        processed_document = {
            "status": "processed",
            "claim_id": claim_id,
            "document_results": document_results,
        }

        workflow_output = Workflow_Output(
            claim_process_id=claim_id, schemaset_id=manifest.schema_collection_id
        )
        workflow_output.workflow_process_outputs.append(
            Executor_Output(
                step_name="document_processing", output_data=processed_document
            )
        )

        await ctx.set_shared_state("workflow_output", workflow_output)
        await ctx.send_message(workflow_output)
