# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Document-processing executor for the claim workflow pipeline.

First step in the three-stage pipeline (document_processing -> summarizing ->
gap_analysis).  Downloads a manifest from blob storage, submits each
referenced file to the content-processing API, polls for completion, and
upserts per-file results into Cosmos DB.
"""

import asyncio
import hashlib
import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path

from agent_framework import Executor, WorkflowContext, handler
from sas.storage.blob.async_helper import AsyncStorageBlobHelper

from libs.application.application_context import AppContext
from repositories.claim_processes import Claim_Process, Claim_Processes, Content_Process
from steps.models.output import Executor_Output, Workflow_Output
from utils.http_request import HttpRequestClient, MultipartFile

from ...models.manifest import ClaimProcess


class DocumentProcessExecutor(Executor):
    """Workflow executor that runs the document-processing step.

    Responsibilities:
        1. Generate a unique, lexicographically sortable claim-process name.
        2. Download ``manifest.json`` from the process-batch blob container.
        3. Create a ``Claim_Process`` record in Cosmos DB.
        4. Submit each manifest item to the content-processing HTTP API.
        5. Poll each submission until terminal status and upsert progress.
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
        """Execute document processing for a claim.

        Steps:
            1. Download ``manifest.json`` from the process-batch container.
            2. Generate a unique claim-process name and persist a new
               ``Claim_Process`` record in Cosmos DB.
            3. Submit each manifest file to the content-processing API via
               multipart POST (concurrency-limited).
            4. Poll each submission until a terminal status (302/404/500).
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

        base_endpoint = (
            self.app_context.configuration.app_cps_content_process_endpoint or ""
        ).rstrip("/")

        submit_path = (
            "/submit"
            if base_endpoint.endswith("/contentprocessor")
            else "/contentprocessor/submit"
        )

        async with HttpRequestClient(base_url=base_endpoint) as client:
            # Limit concurrency to avoid overwhelming the service
            max_concurrency = 2
            semaphore = asyncio.Semaphore(max_concurrency)
            poll_interval_seconds = float(
                getattr(
                    self.app_context.configuration,
                    "app_cps_poll_interval_seconds",
                    5.0,
                )
            )

            def _extract_process_id(value: str | None) -> str | None:
                if not value:
                    return None
                # Accept either a bare id or a URL/path ending with the id.
                cleaned = value.rstrip("/")
                last = cleaned.split("/")[-1]
                return last or None

            async def _process_one(item) -> dict:
                async with semaphore:
                    try:
                        process_id: str | None = None
                        seen_progress_digests: set[str] = set()
                        source_file = await storage_helper.download_blob(
                            container_name=self.app_context.configuration.app_cps_process_batch,
                            blob_name=f"{claim_id}/{item.file_name}",
                        )

                        filename = Path(str(item.file_name)).name
                        content_type, _ = mimetypes.guess_type(filename)

                        if isinstance(source_file, (bytes, bytearray, memoryview)):
                            file_bytes = bytes(source_file)
                        else:
                            file_bytes = bytes(source_file)

                        json_payload = {
                            "Metadata_Id": f"Meta-{uuid.uuid4()}"
                            if not item.metadata_id
                            else item.metadata_id,
                            "Schema_Id": str(item.schema_id),
                        }

                        print(
                            f"Processing document: {item.file_name} with schema_id: {item.schema_id}"
                        )

                        response = await client.post_multipart_json(
                            submit_path,
                            json_part_name="data",
                            json_payload=json_payload,
                            files=[
                                MultipartFile(
                                    field_name="file",
                                    filename=filename,
                                    content=file_bytes,
                                    content_type=content_type
                                    or "application/octet-stream",
                                )
                            ],
                            expected_status=(200, 202),
                        )

                        # Best-effort: capture process_id from submit response.
                        if response.body:
                            try:
                                submit_payload = response.json()
                                process_id = (
                                    submit_payload.get("process_id") or process_id
                                )
                            except Exception:
                                pass

                        # Status contract:
                        # - processing: 200
                        # - completed: 302
                        # - not found: 404
                        # - error: 500
                        if response.status in (200, 202):
                            poll_url = (
                                response.header("Operation-Location")
                                or response.header("Location")
                                or response.url
                            )

                            async def _on_poll(r):
                                nonlocal process_id
                                nonlocal seen_progress_digests

                                if r.status not in (200, 500) or not r.body:
                                    return

                                digest = hashlib.sha256(r.body).hexdigest()
                                if digest in seen_progress_digests:
                                    return
                                seen_progress_digests.add(digest)
                                # Avoid unbounded growth on very chatty endpoints.
                                if len(seen_progress_digests) > 64:
                                    seen_progress_digests.clear()

                                print(
                                    f"[DocumentProcess progress] {item.file_name}: {r.text()}"
                                )

                                try:
                                    payload = r.json()
                                except Exception:
                                    payload = None

                                if not isinstance(payload, dict):
                                    return

                                process_id = payload.get("process_id") or process_id
                                current_process_id = (
                                    payload.get("process_id") or process_id
                                )

                                status = payload.get("status")
                                if r.status == 500 and not status:
                                    status = "Failed"

                                await claim_process_repository.Upsert_Content_Process(
                                    process_id=claim_id,
                                    content_process=Content_Process(
                                        process_id=current_process_id,
                                        file_name=str(item.file_name),
                                        mime_type=content_type
                                        or "application/octet-stream",
                                        status=status,
                                    ),
                                )

                            response = await client.poll_until_done(
                                poll_url,
                                method="GET",
                                pending_statuses=(202, 200),
                                done_statuses=(302, 404, 500),
                                poll_interval_seconds=poll_interval_seconds,
                                timeout_seconds=600.0,  # TODO: Make configurable if needed
                                on_poll=_on_poll,
                            )

                        # Capture process_id from the final redirect URL if needed.
                        if not process_id:
                            process_id = _extract_process_id(
                                response.header("Location")
                                or response.header("Operation-Location")
                                or response.url
                            )

                        # Final output fetch + Cosmos upsert (single task per file).
                        status_code = response.status
                        if status_code in (200, 202):
                            status_text = "Processing"
                        elif status_code == 302:
                            status_text = "Completed"
                        elif status_code == 404:
                            status_text = "Failed"
                        elif status_code == 500:
                            status_text = "Failed"
                        else:
                            status_text = "Failed"

                        schema_score_f = 0.0
                        entity_score_f = 0.0
                        processed_time = ""

                        if status_code in (302, 404, 500) and process_id:
                            final_output_path = (
                                f"/{process_id}"
                                if base_endpoint.endswith("/contentprocessor")
                                else f"/contentprocessor/processed/{process_id}"
                            )
                            try:
                                final_resp = await client.get(
                                    final_output_path,
                                    expected_status=(200, 404, 500),
                                )
                                if final_resp.body:
                                    try:
                                        final_payload = final_resp.json()
                                    except Exception:
                                        final_payload = None

                                    if isinstance(final_payload, dict):
                                        status_text = (
                                            final_payload.get("status") or status_text
                                        )
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
                                                final_payload.get("processed_time")
                                                or ""
                                            )
                                        except Exception:
                                            processed_time = ""
                            except Exception as e:
                                print(
                                    f"[DocumentProcess] Failed to fetch final output for {process_id}: {type(e).__name__}: {e}"
                                )
                        if process_id:
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

                        try:
                            result_payload = response.json() if response.body else None
                        except Exception:
                            result_payload = response.text() if response.body else None

                        return {
                            "file_name": str(item.file_name),
                            "schema_id": str(item.schema_id),
                            "mime_type": content_type or "application/octet-stream",
                            "process_id": process_id,
                            "status": response.status,
                            "final_status": status_text,
                            "schema_score": schema_score_f,
                            "entity_score": entity_score_f,
                            "response": result_payload,
                            "poll_url": response.header("Location")
                            or response.header("Operation-Location")
                            or response.url,
                        }
                    except Exception as e:
                        # Ensure the failure is reflected in Cosmos so the
                        # status doesn't remain at the last polling value
                        # (e.g. "Extract").
                        error_process_id = process_id
                        if not error_process_id:
                            error_process_id = _extract_process_id(None)
                        if error_process_id:
                            try:
                                await claim_process_repository.Upsert_Content_Process(
                                    process_id=claim_id,
                                    content_process=Content_Process(
                                        process_id=error_process_id,
                                        file_name=str(
                                            getattr(item, "file_name", "<unknown>")
                                        ),
                                        mime_type=content_type
                                        or "application/octet-stream",
                                        status="Failed",
                                    ),
                                )
                            except Exception:
                                pass

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

            # TODO: Remove files in process batch container after processing (if desired)

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
