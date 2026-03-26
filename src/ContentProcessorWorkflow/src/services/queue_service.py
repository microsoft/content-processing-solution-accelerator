# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Queue-based Claim Processing Service.

This module implements a background queue worker that consumes claim batch
processing requests from an Azure Storage Queue and executes the step-based
workflow runner in ``src/steps/claim_processor.py``.

Architecture
------------
- **Entry point**: ``main_service.py`` creates a ``ClaimProcessingQueueService``
  instance and calls ``start_service()``, which spawns one or more async
  worker loops.
- **Worker loop** (``_worker_loop``): each worker long-polls the queue for a
  single message at a time, wraps the processing in an ``asyncio.Task``, and
  awaits it.
- **Message processing** (``_process_queue_message``): parses the JSON payload
  to extract ``claim_process_id``, starts a visibility-timeout renewal loop,
  then delegates to ``ClaimProcessor.run()``.
- **Visibility renewal** (``_renew_visibility_loop``): runs concurrently with
  the job and re-extends the visibility timeout at ~60 % intervals so long-
  running jobs don't become visible to other consumers.

Message lifecycle
-----------------
1. Message is dequeued with ``visibility_timeout_minutes`` (default 30 min).
2. On **success**: the message is deleted from the queue.
3. On **failure** (attempt < ``max_receive_attempts``): the visibility timeout
   is shortened to ``retry_visibility_delay_seconds`` so the message becomes
   available again quickly.
4. On **final failure** (attempt >= ``max_receive_attempts``):
   a. A JSON payload containing the original content and failure reason is
      sent to the dead-letter queue.
   b. Output blobs under ``<claim_process_id>/converted/`` are deleted.
   c. The original message is deleted from the main queue.
   d. If the dead-letter send fails, the original message is kept (visibility
      is extended) to avoid silent data loss.
5. Malformed messages (invalid JSON, missing ``claim_process_id``) are
   immediately dead-lettered regardless of attempt count.
"""

import asyncio
import base64
import json
import logging
import time
from dataclasses import dataclass
from urllib.parse import urlparse

from azure.core.exceptions import AzureError, ResourceNotFoundError
from azure.storage.queue import QueueClient, QueueMessage, QueueServiceClient
from sas.storage import StorageBlobHelper

from libs.application.application_context import AppContext
from steps.claim_processor import ClaimProcessor, WorkflowExecutorFailedException
from steps.models.request import ClaimProcessTaskParameters
from utils.credential_util import get_azure_credential
from utils.logging_utils import configure_application_logging

configure_application_logging(debug_mode=False)

logger = logging.getLogger(__name__)


def parse_claim_task_parameters_from_queue_content(
    raw_content: str | bytes,
) -> ClaimProcessTaskParameters:
    """Parse a queue message payload into ``ClaimProcessTaskParameters``.

    Azure Storage Queue may base64-encode message content automatically.
    This function handles both raw JSON and base64-wrapped JSON transparently.

    Processing steps:
    1. Convert ``bytes`` to ``str`` (UTF-8).
    2. Attempt base64 decode with ``validate=True`` — this only succeeds for
       strings that are strict base64.  If decoding succeeds the result
       replaces the original content; otherwise the original is kept.
    3. Validate that the content starts with ``{`` (JSON object).
    4. Parse JSON and extract the required ``claim_process_id`` field.

    Args:
        raw_content: The raw ``QueueMessage.content`` value (``str`` or
            ``bytes``).

    Returns:
        A ``ClaimProcessTaskParameters`` instance with a non-empty
        ``claim_process_id``.

    Raises:
        ValueError: If the content is empty, not valid JSON, or missing /
            empty ``claim_process_id``.
    """

    if raw_content is None:  # type: ignore[truthy-bool]
        raise ValueError("Queue message content is empty")

    if isinstance(raw_content, bytes):
        content = raw_content.decode("utf-8")
    else:
        content = str(raw_content)

    # Try base64 decode (validate=True avoids decoding arbitrary strings).
    try:
        decoded = base64.b64decode(content, validate=True)
        try:
            content = decoded.decode("utf-8")
        except UnicodeDecodeError:
            pass
    except Exception:
        pass

    content = content.strip()
    if not content:
        raise ValueError("Queue message content is empty")

    if not content.startswith("{"):
        raise ValueError(
            'Queue message must be JSON with \'claim_process_id\' (example: {"claim_process_id": "..."}).'
        )

    data = json.loads(content)
    if not isinstance(data, dict):
        raise ValueError("Queue message JSON must be an object")

    if "claim_process_id" not in data:
        raise ValueError("Queue JSON must include 'claim_process_id'")

    claim_process_id = str(data.get("claim_process_id") or "").strip()
    if not claim_process_id:
        raise ValueError("claim_process_id is empty")

    return ClaimProcessTaskParameters(claim_process_id=claim_process_id)


@dataclass
class QueueServiceConfig:
    """Configuration dataclass for ``ClaimProcessingQueueService``.

    Authentication always uses Azure Default Credential (Entra ID).

    Attributes:
        storage_account_name: Azure Storage account name (or full URL).
            Used to build the ``https://<name>.queue.core.windows.net`` endpoint.
        queue_name: Name of the main processing queue.
        dead_letter_queue_name: Name of the dead-letter queue for failed
            messages.  Falls back to ``<queue_name>-dead-letter-queue``.
        visibility_timeout_minutes: How long a dequeued message stays
            invisible to other consumers (minutes).  The visibility-renewal
            loop extends this periodically while the job is running.
        concurrent_workers: Number of parallel async worker loops.  Each
            worker dequeues and processes one message at a time.
        poll_interval_seconds: Sleep duration between queue polls when no
            message is received.
        max_receive_attempts: Maximum ``dequeue_count`` before a failed
            message is sent to the dead-letter queue.
        retry_visibility_delay_seconds: Shortened visibility timeout applied
            to a failed message so it becomes available for retry sooner.
    """

    use_entra_id: bool = True
    storage_account_name: str = ""  # Storage account name for default credential auth
    queue_name: str = "claim-process-queue"
    dead_letter_queue_name: str = "claim-process-dead-letter-queue"
    visibility_timeout_minutes: int = 30
    concurrent_workers: int = 1  # Number of parallel queue workers
    poll_interval_seconds: int = 5
    message_timeout_minutes: int = 25
    control_poll_interval_seconds: int = 2
    max_receive_attempts: int = 3
    retry_visibility_delay_seconds: int = 5


class ClaimProcessingQueueService:
    """Background queue worker that processes claim batch requests.

    Polls an Azure Storage Queue, dispatches each message to the step-based
    workflow runner (``ClaimProcessor``), and manages visibility-timeout
    renewal to prevent duplicate processing.

    Concurrency model:
        ``start_service()`` spawns ``concurrent_workers`` async tasks, each
        running ``_worker_loop()``.  Within a worker, each message is
        processed by a separate child ``asyncio.Task`` so that
        ``stop_process()`` can cancel a single job without tearing down the
        worker loop.

    Instance tracking:
        A class-level ``_instance_count`` / ``_active_instances`` set is
        maintained so that ``stop_service()`` can detect and prevent ghost
        processes when a new instance replaces an old one.

    In-flight tracking dictionaries (keyed by ``worker_id``):
        - ``_worker_inflight``: current ``process_id`` (observability).
        - ``_worker_inflight_message``: ``(message_id, pop_receipt)`` so the
          message can be deleted or its visibility updated at any time.
        - ``_worker_inflight_batch_id``: ``claim_process_id`` used for blob
          cleanup on failure.
        - ``_worker_inflight_task``: the child ``asyncio.Task`` running the
          job, allowing targeted cancellation.

    Retry + dead-letter policy:
        - Failed messages are retried up to ``max_receive_attempts``
          (Azure's ``dequeue_count``).
        - On the final attempt the payload and failure reason are sent to
          the dead-letter queue, output blobs are cleaned up, then the
          original message is deleted.
        - If the dead-letter send itself fails, the original message is
          kept (visibility extended) to prevent silent data loss.
    """

    # Class-level tracking to prevent multiple instances and detect ghost processes
    _instance_count = 0
    _active_instances = set()
    main_queue: QueueClient | None = None
    dead_letter_queue: QueueClient | None = None

    def __init__(
        self,
        config: QueueServiceConfig,
        app_context: AppContext | None = None,
        debug_mode: bool = False,
    ):
        # Increment instance counter and track this instance
        ClaimProcessingQueueService._instance_count += 1
        self.instance_id = ClaimProcessingQueueService._instance_count
        ClaimProcessingQueueService._active_instances.add(self.instance_id)

        logger.info(
            "Creating Claim Processing Queue Service instance #%s", self.instance_id
        )
        logger.info(
            f"Active instances: {len(ClaimProcessingQueueService._active_instances)} - IDs: {list(ClaimProcessingQueueService._active_instances)}"
        )

        if app_context is None:
            raise ValueError("app_context must be provided to QueueMigrationService")

        self.config = config
        self.app_context: AppContext = app_context
        # Controlled by the caller (main_service.py), not app configuration.
        self.debug_mode = debug_mode
        self.is_running = False

        # Initialize Azure Queue Service with Default Credential
        credential = get_azure_credential()
        storage_account_url = (
            f"https://{config.storage_account_name}.queue.core.windows.net"
        )
        self.queue_service = QueueServiceClient(
            account_url=storage_account_url, credential=credential
        )

        # Initialize queues
        self.main_queue = self.queue_service.get_queue_client(config.queue_name)
        dead_name = (config.dead_letter_queue_name or "").strip()
        if not dead_name:
            dead_name = f"{config.queue_name}-dead-letter-queue"
        self.dead_letter_queue = self.queue_service.get_queue_client(dead_name)

        # Worker tracking
        self.active_workers = set()
        self._worker_tasks: dict[int, asyncio.Task] = {}

        # Track the currently running process_id per worker for observability.
        self._worker_inflight: dict[int, str] = {}

        # Track the in-flight queue message per worker so we can delete it on kill.
        self._worker_inflight_message: dict[int, tuple[str, str]] = {}

        # Track the in-flight workflow input per worker (used for resource cleanup).
        self._worker_inflight_batch_id: dict[int, str] = {}

        # Track the in-flight job task per worker so we can cancel only the job (not the worker).
        self._worker_inflight_task: dict[int, asyncio.Task] = {}

    async def start_service(self):
        """Start polling workers and block until all workers exit or are cancelled.

        Flow:
        1. Calls ``_ensure_queues_exist()`` to create the main and dead-letter
           queues if they don't exist yet (idempotent).
        2. Spawns ``concurrent_workers`` async tasks, each running
           ``_worker_loop(worker_id)``.
        3. ``asyncio.gather`` blocks until every worker finishes.
           ``CancelledError`` from a worker is treated as expected (e.g.
           triggered by ``stop_service()``).
        4. If any worker raises a non-cancellation exception, that exception
           is re-raised to the caller.
        5. On exit (normal or exception), ``is_running`` is set to ``False``
           and the worker-tasks dict is cleared.
        """
        if self.is_running:
            logger.warning("Service is already running")
            return

        self.is_running = True
        logger.info(
            "Starting Claim Processing Queue Service with %s worker(s)",
            self.config.concurrent_workers,
        )

        try:
            await self._ensure_queues_exist()

            worker_count = max(1, int(self.config.concurrent_workers or 1))
            logger.info("Spawning %s queue worker(s)", worker_count)

            self._worker_tasks = {
                worker_id: asyncio.create_task(
                    self._worker_loop(worker_id),
                    name=f"queue-worker-{worker_id}",
                )
                for worker_id in range(1, worker_count + 1)
            }

            results = await asyncio.gather(
                *self._worker_tasks.values(), return_exceptions=True
            )
            for result in results:
                # CancelledError is expected when stop_service()/stop_worker() cancels workers.
                if isinstance(result, asyncio.CancelledError):
                    continue
                if isinstance(result, Exception):
                    logger.error("Queue worker exited with error: %s", result)
                    raise result

        except Exception as e:
            logger.error(f"Error starting queue service: {e}")
            raise
        finally:
            self.is_running = False
            self._worker_tasks.clear()

    async def stop_service(self):
        """Gracefully stop all workers, cancel in-flight jobs, and close queue clients.

        Shutdown sequence:
        1. Set ``is_running = False`` immediately — worker loops check this
           flag on each iteration and will exit on the next cycle.
        2. Remove this instance from the class-level ``_active_instances``
           set to prevent ghost-process detection false positives.
        3. Cancel all worker ``asyncio.Task`` objects and await their
           completion (``CancelledError`` is swallowed).
        4. Cancel all in-flight per-message job tasks separately, because
           cancelling the outer worker loop does not reliably propagate to
           the inner job task.
        5. Clear all in-flight tracking dictionaries.
        6. Close the ``main_queue``, ``dead_letter_queue``, and
           ``queue_service`` SDK clients.

        Note:
            Cancelling a worker while it holds a message may leave the
            message invisible until the visibility timeout expires, at which
            point another consumer will pick it up.
        """
        logger.info(
            "Stopping Claim Processing Queue Service instance #%s - setting is_running=False",
            self.instance_id,
        )

        # CRITICAL: Set is_running to False IMMEDIATELY to prevent ghost processes
        self.is_running = False
        logger.info(
            f"Queue service instance #{self.instance_id} is_running flag set to: {self.is_running}"
        )

        # Remove from active instances tracking
        if self.instance_id in ClaimProcessingQueueService._active_instances:
            ClaimProcessingQueueService._active_instances.remove(self.instance_id)
            logger.info(f"Removed instance #{self.instance_id} from active instances")
            logger.info(
                f"Remaining active instances: {len(ClaimProcessingQueueService._active_instances)} - IDs: {list(ClaimProcessingQueueService._active_instances)}"
            )

        # Cancel any active worker tasks
        if self._worker_tasks:
            logger.info(
                "Cancelling %s worker task(s) for instance #%s",
                len(self._worker_tasks),
                self.instance_id,
            )
            for task in self._worker_tasks.values():
                task.cancel()
            await asyncio.gather(*self._worker_tasks.values(), return_exceptions=True)
            self._worker_tasks.clear()

        # Cancel any in-flight job tasks. Cancelling the worker loop does
        # not reliably cancel the per-message job task.
        if self._worker_inflight_task:
            inflight_tasks = list(self._worker_inflight_task.values())
            logger.info(
                "Cancelling %s in-flight job task(s) for instance #%s",
                len(inflight_tasks),
                self.instance_id,
            )
            for task in inflight_tasks:
                task.cancel()
            await asyncio.gather(*inflight_tasks, return_exceptions=True)
            self._worker_inflight_task.clear()

        # Clear inflight tracking
        self._worker_inflight.clear()
        self._worker_inflight_message.clear()
        self._worker_inflight_batch_id.clear()
        self._worker_inflight_task.clear()

        # Close queue clients
        try:
            if self.main_queue:
                self.main_queue.close()
        except Exception:
            pass

        try:
            if self.dead_letter_queue:
                self.dead_letter_queue.close()
        except Exception:
            pass

        try:
            self.queue_service.close()
        except Exception:
            pass

    async def force_stop(self):
        """Alias for ``stop_service()`` (stop already cancels worker tasks)."""

        await self.stop_service()

    async def stop_process(
        self, process_id: str, timeout_seconds: float = 10.0
    ) -> bool:
        """Hard-kill an in-flight process by ``process_id``.

        Looks up which worker is currently processing ``process_id`` by
        scanning ``_worker_inflight``.  If found, executes a three-step
        teardown:

        1. **Delete queue message** — calls ``_delete_inflight_queue_message``
           using the tracked ``(message_id, pop_receipt)`` so the message
           won't become visible again after the timeout.
        2. **Delete output blobs** — removes blobs under
           ``<claim_process_id>/converted/`` via ``_cleanup_output_blobs``
           to prevent stale partial output.
        3. **Cancel the job task** — cancels only the per-message
           ``asyncio.Task`` (not the worker loop itself), waits up to
           ``timeout_seconds`` for it to finish, and swallows
           ``CancelledError`` / ``TimeoutError``.

        After cancellation the worker loop continues polling for new
        messages.

        Args:
            process_id: The ``claim_process_id`` of the running job.
            timeout_seconds: Maximum time to wait for the job task to
                acknowledge cancellation.

        Returns:
            ``True`` if the process was found and killed, ``False`` if no
            worker is currently processing that ``process_id``.
        """

        target_worker_id = None
        for worker_id, inflight_process_id in self._worker_inflight.items():
            if inflight_process_id == process_id:
                target_worker_id = worker_id
                break

        if not target_worker_id:
            logger.warning(
                "Requested kill for process_id=%s but no worker is inflight",
                process_id,
            )
            return False

        logger.warning(
            "Hard-kill requested for process_id=%s (worker_id=%s)",
            process_id,
            target_worker_id,
        )

        # 1) Delete the queue message. This prevents re-processing.
        await self._delete_inflight_queue_message(target_worker_id)

        # 2) Delete output blobs for this process.
        batch_id = self._worker_inflight_batch_id.get(target_worker_id)
        if batch_id:
            await self._cleanup_output_blobs(batch_id)
        else:
            logger.warning(
                "No batch_id tracked for worker_id=%s; skipping blob cleanup",
                target_worker_id,
            )

        # 3) Cancel only the in-flight job task (worker loop continues).
        job_task = self._worker_inflight_task.get(target_worker_id)
        if job_task:
            job_task.cancel()
            try:
                await asyncio.wait_for(
                    asyncio.shield(job_task), timeout=timeout_seconds
                )
            except asyncio.CancelledError:
                # Expected: we intentionally cancelled the in-flight job.
                pass
            except asyncio.TimeoutError:
                logger.warning(
                    "Timed out waiting for job cancellation process_id=%s worker_id=%s",
                    process_id,
                    target_worker_id,
                )
            except Exception:
                pass

        return True

    async def stop_worker(self, worker_id: int, timeout_seconds: float = 5.0) -> bool:
        """Stop a specific worker by cancelling its ``asyncio.Task``.

        Prefer ``stop_process(process_id)`` for a clean per-job teardown.
        Use this method only when you need to remove an entire worker loop
        (e.g. to scale down the number of concurrent workers at runtime).

        Behaviour:
        1. Cancels the worker's ``asyncio.Task`` and waits up to
           ``timeout_seconds`` for it to exit.
        2. Removes all tracking state for that worker (inflight message,
           batch id, job task, active-workers set).

        Caveat:
            If the worker is mid-message, the queue message is **not**
            explicitly deleted — it will become visible again after the
            visibility timeout expires and will be re-processed by another
            worker.

        Args:
            worker_id: Integer id assigned when the worker was spawned.
            timeout_seconds: Maximum time to wait for the task to
                acknowledge cancellation.

        Returns:
            ``True`` if the worker existed and was cancelled, ``False`` if
            no task was found for the given ``worker_id``.
        """

        task = self._worker_tasks.get(worker_id)
        if not task:
            logger.warning("Requested stop for missing worker_id=%s", worker_id)
            return False

        inflight = self._worker_inflight.get(worker_id)
        if inflight:
            logger.info(
                "Stopping worker %s (inflight process_id=%s)", worker_id, inflight
            )
        else:
            logger.info("Stopping worker %s", worker_id)

        task.cancel()
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            logger.warning(
                "Timed out waiting for worker %s to stop; task will remain cancelled",
                worker_id,
            )
        except Exception:
            # Cancellation typically raises CancelledError which is fine.
            pass
        finally:
            self._worker_tasks.pop(worker_id, None)
            self._worker_inflight.pop(worker_id, None)
            self._worker_inflight_message.pop(worker_id, None)
            self._worker_inflight_batch_id.pop(worker_id, None)
            self._worker_inflight_task.pop(worker_id, None)
            self.active_workers.discard(worker_id)

        return True

    def _storage_account_name(self) -> str:
        """Extract a short storage account name from ``config.storage_account_name``.

        The config value may be supplied in several formats:
        - Plain account name: ``"mystorage"`` → returned as-is.
        - Full URL: ``"https://mystorage.queue.core.windows.net"`` → the
          hostname is parsed and the first label (``mystorage``) is returned.
        - FQDN: ``"mystorage.queue.core.windows.net"`` → split on ``'.'``
          and the first label is returned.

        Returns:
            The short account name, or an empty string if not configured.
        """

        raw = (self.config.storage_account_name or "").strip()
        if not raw:
            return raw

        if raw.startswith("http://") or raw.startswith("https://"):
            host = urlparse(raw).netloc
            return host.split(".")[0] if host else raw

        # If user passed a hostname like "mystorage.queue.core.windows.net"
        if "." in raw:
            return raw.split(".")[0]

        return raw

    async def _delete_inflight_queue_message(self, worker_id: int):
        """Delete the queue message currently held by a worker.

        Looks up the ``(message_id, pop_receipt)`` tuple tracked in
        ``_worker_inflight_message[worker_id]`` and issues a synchronous
        ``delete_message`` call to Azure Storage.

        If the message was already deleted (e.g. visibility expired and
        another consumer processed it), ``ResourceNotFoundError`` is
        logged at INFO level and silently ignored.
        """

        msg = self._worker_inflight_message.get(worker_id)
        if not msg:
            logger.warning(
                "No inflight queue message tracked for worker_id=%s", worker_id
            )
            return

        message_id, pop_receipt = msg
        try:
            if self.main_queue:
                self.main_queue.delete_message(message_id, pop_receipt)
                logger.info(
                    "Deleted inflight queue message worker_id=%s message_id=%s",
                    worker_id,
                    message_id,
                )
        except ResourceNotFoundError:
            # Message was already deleted or pop_receipt expired.
            logger.info(
                "Inflight queue message already gone worker_id=%s message_id=%s",
                worker_id,
                message_id,
            )
        except AzureError as e:
            logger.error(
                "Failed to delete inflight queue message worker_id=%s message_id=%s err=%s",
                worker_id,
                message_id,
                e,
            )

    async def _cleanup_output_blobs(self, claim_process_id: str):
        """Delete the output folder blobs for a batch process.

        Runs ``_cleanup_output_blobs_sync`` in a thread via
        ``asyncio.to_thread`` so that the synchronous Azure SDK calls
        don't block the event loop.
        """

        await asyncio.to_thread(self._cleanup_output_blobs_sync, claim_process_id)

    def _cleanup_output_blobs_sync(self, claim_process_id: str):
        """Synchronously delete output blobs under ``<claim_process_id>/converted/``.

        Steps:
        1. Resolve the storage account name and container name from config.
        2. List all blobs under the ``<claim_process_id>/converted/`` prefix,
           filtering out directory marker entries (ADLS Gen2 / HNS).
        3. Bulk-delete the listed blobs via ``StorageBlobHelper.delete_multiple_blobs``.
        4. For ADLS Gen2 (hierarchical namespace) accounts, attempt to
           remove the directory entry itself using the ``azure.storage.filedatalake``
           SDK.  This import is done lazily — if the package is not
           installed the step is silently skipped.

        This method is designed to be called from ``asyncio.to_thread`` and
        must not use any ``await`` expressions.
        """

        account = self._storage_account_name() or (
            getattr(self.app_context.configuration, "app_storage_account_name", "")
            or ""
        )
        if not account:
            logger.warning(
                "No storage account configured; skipping output blob cleanup"
            )
            return

        credential = get_azure_credential()

        output_prefix = f"{claim_process_id}/converted"

        # Normalize to a folder-like prefix.
        output_prefix = output_prefix.strip("/") + "/"

        container_name = (
            getattr(self.app_context.configuration, "app_cps_process_batch", None)
            or getattr(self.app_context.configuration, "app_storage_container", None)
            or ""
        )
        if not container_name:
            logger.warning("No blob container configured; skipping output blob cleanup")
            return

        def _is_directory_entry(entry: dict) -> bool:
            try:
                if entry.get("is_directory") is True:
                    return True
                if str(entry.get("is_directory", "")).strip().lower() in {
                    "true",
                    "1",
                    "yes",
                }:
                    return True

                kind = (
                    str(entry.get("type", "") or entry.get("resource_type", ""))
                    .strip()
                    .lower()
                )
                if kind in {"directory", "dir", "folder"}:
                    return True
            except Exception:
                return False
            return False

        try:
            helper = StorageBlobHelper(account_name=account, credential=credential)
            blobs = helper.list_blobs(container_name, prefix=output_prefix)

            blob_names: list[str] = []
            output_dir_name = output_prefix.rstrip("/")
            for b in blobs:
                name = (b.get("name") or "").strip()
                if not name:
                    continue
                if _is_directory_entry(b):
                    continue
                # Some helpers may return the directory itself (without trailing '/').
                if name.rstrip("/") == output_dir_name:
                    continue
                blob_names.append(name)
            if not blob_names:
                logger.info(
                    "Output cleanup: no blobs found claim_process_id=%s container=%s prefix=%s",
                    claim_process_id,
                    container_name,
                    output_prefix,
                )
                return

            results = helper.delete_multiple_blobs(container_name, blob_names)
            deleted = sum(1 for ok in results.values() if ok)

            # Remove the output directory entry itself for ADLS Gen2 (HNS).
            try:
                import importlib

                dl_mod = importlib.import_module("azure.storage.filedatalake")
                DataLakeServiceClient = getattr(dl_mod, "DataLakeServiceClient")

                dl = DataLakeServiceClient(
                    account_url=f"https://{account}.dfs.core.windows.net",
                    credential=credential,
                )
                fs = dl.get_file_system_client(container_name)
                dir_client = fs.get_directory_client(output_dir_name)
                try:
                    dir_client.delete_directory(recursive=True)
                except TypeError as te:
                    if "recursive" in str(te) and "multiple values" in str(te):
                        dir_client.delete_directory()
                    else:
                        raise
            except Exception as e:
                logger.info(
                    "Output directory delete skipped/failed claim_process_id=%s container=%s dir=%s err=%s",
                    claim_process_id,
                    container_name,
                    output_dir_name,
                    e,
                )

            logger.warning(
                "Output cleanup complete claim_process_id=%s container=%s prefix=%s deleted=%s",
                claim_process_id,
                container_name,
                output_prefix,
                deleted,
            )
        except Exception as e:
            logger.error(
                "Output cleanup failed claim_process_id=%s container=%s prefix=%s err=%s",
                claim_process_id,
                container_name,
                output_prefix,
                e,
            )

    ######################################################
    # Queue message processing
    ######################################################
    async def process_message(self):
        """Single-worker entrypoint (kept for backward compatibility)."""

        await self._worker_loop(worker_id=1)

    async def _worker_loop(self, worker_id: int):
        """Poll the queue in a loop, dispatching each message to ``_process_queue_message``.

        Loop structure (runs while ``is_running`` is ``True``):
        1. Call ``main_queue.receive_messages(max_messages=1)`` with the
           configured visibility timeout.
        2. If a message is received, wrap ``_process_queue_message`` in an
           ``asyncio.Task`` and ``await`` it.  The task reference is stored
           in ``_worker_inflight_task`` so ``stop_process()`` can cancel it.
        3. If the job task raises ``CancelledError``, log a warning and
           continue to the next iteration (intentional cancellation).
        4. If the job task raises any other exception, attempt to dead-letter
           the message so the failure is not silently lost, then continue.
        5. If no message was received, sleep for ``poll_interval_seconds``
           before polling again.

        Error handling:
        - Transient queue-receive errors (network / storage) are logged and
          the worker sleeps before retrying — the loop is never exited due
          to a receive error.
        - ``CancelledError`` at the top level is re-raised so that
          ``stop_service()`` / ``stop_worker()`` can cleanly shut down.
        - On exit the worker removes itself from ``active_workers`` and
          ``_worker_inflight``.
        """

        self.active_workers.add(worker_id)
        logger.info("[worker %s] started", worker_id)

        try:
            while self.is_running:
                if not self.main_queue:
                    await asyncio.sleep(self.config.poll_interval_seconds)
                    continue

                received_any = False
                try:
                    for queue_message in self.main_queue.receive_messages(
                        max_messages=1,
                        visibility_timeout=self.config.visibility_timeout_minutes * 60,
                    ):
                        received_any = True
                        job_task = asyncio.create_task(
                            self._process_queue_message(worker_id, queue_message),
                            name=f"queue-job-{worker_id}",
                        )
                        self._worker_inflight_task[worker_id] = job_task

                        try:
                            await job_task
                        except asyncio.CancelledError:
                            # Cancelled intentionally via stop_process/stop_service.
                            logger.warning(
                                "[worker %s] in-flight job cancelled", worker_id
                            )
                        except Exception:
                            # Defensive: a job should never crash the worker.
                            logger.exception(
                                "[worker %s] job task crashed unexpectedly", worker_id
                            )

                            # Dead-letter the message so the crash is not silently lost.
                            try:
                                inflight_pid = self._worker_inflight.get(
                                    worker_id, "<unknown>"
                                )
                                inflight_batch_id = self._worker_inflight_batch_id.get(
                                    worker_id
                                )
                                await self._handle_failed_no_retry(
                                    queue_message=queue_message,
                                    process_id=inflight_pid,
                                    failure_reason="Job task crashed unexpectedly",
                                    execution_time=0.0,
                                    claim_process_id_for_cleanup=inflight_batch_id,
                                    worker_id=worker_id,
                                )
                            except Exception:
                                logger.exception(
                                    "[worker %s] failed to handle crashed job task",
                                    worker_id,
                                )
                        finally:
                            self._worker_inflight_task.pop(worker_id, None)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    # Defensive: queue receive can fail transiently (network/storage).
                    # Don't exit the worker; log and continue polling.
                    logger.exception(
                        "[worker %s] queue receive loop error (will continue)",
                        worker_id,
                    )
                    await asyncio.sleep(self.config.poll_interval_seconds)

                if not received_any:
                    await asyncio.sleep(self.config.poll_interval_seconds)
        except asyncio.CancelledError:
            # Task was cancelled intentionally (stop_service/stop_worker).
            raise
        finally:
            self._worker_inflight.pop(worker_id, None)
            self.active_workers.discard(worker_id)
            logger.info("[worker %s] stopped", worker_id)

    async def _process_queue_message(self, worker_id: int, queue_message: QueueMessage):
        """Parse, execute, and finalise one queue message via ``ClaimProcessor``.

        Lifecycle of a single message:
        1. **Parse** — call ``_build_task_param`` to extract
           ``claim_process_id`` from the JSON payload.  If parsing fails the
           message is immediately dead-lettered (``force_dead_letter=True``)
           regardless of attempt count.
        2. **Track** — store ``claim_process_id``, ``(message_id, pop_receipt)``,
           and ``batch_id`` in the per-worker inflight dictionaries.
        3. **Renew visibility** — start ``_renew_visibility_loop`` as a
           concurrent task so that long-running jobs don't lose their lease.
        4. **Execute** — resolve ``ClaimProcessor`` from the DI container
           (``app_context.get_service``) and call ``claim_processor.run()``.
        5. **Finalise**:
           - On success: ``_handle_successful_processing`` deletes the message.
           - On failure: ``_handle_failed_no_retry`` either schedules a
             retry or dead-letters the message.
        6. **Cleanup** — cancel the visibility-renewal task and clear the
           per-worker tracking dictionaries in a ``finally`` block.

        This method is designed to never raise (except ``CancelledError``),
        so a single bad message cannot crash the worker loop.
        """

        message_start_time = time.time()

        # Ensure this function never raises (except CancelledError), so a single
        # bad message can't crash the entire service.
        claim_process_id: str = "<unknown>"
        renew_task: asyncio.Task | None = None

        try:
            logger.info(
                "[worker %s] Message dequeued from %s - %s",
                worker_id,
                getattr(self.main_queue, "queue_name", "<unknown>"),
                getattr(queue_message, "content", "<no-content>"),
            )

            # Parse queue payload into the workflow input model.
            try:
                claim_process_id = self._build_task_param(queue_message)
            except Exception as e:
                execution_time = time.time() - message_start_time
                reason = f"Invalid queue message: {e}"

                logger.error(
                    "[worker %s] %s message_id=%s raw=%s",
                    worker_id,
                    reason,
                    getattr(queue_message, "id", "<unknown>"),
                    getattr(queue_message, "content", "<no-content>"),
                )

                await self._handle_failed_no_retry(
                    queue_message,
                    claim_process_id,
                    reason,
                    execution_time,
                    claim_process_id_for_cleanup=None,
                    worker_id=worker_id,
                    force_dead_letter=True,
                )
                return

            self._worker_inflight[worker_id] = claim_process_id
            self._worker_inflight_batch_id[worker_id] = claim_process_id

            message_id = getattr(queue_message, "id", None)
            pop_receipt = getattr(queue_message, "pop_receipt", None)
            if message_id is not None and pop_receipt is not None:
                self._worker_inflight_message[worker_id] = (
                    str(message_id),
                    str(pop_receipt),
                )

            # Renew visibility timeout while the job is running to prevent duplicate processing
            # if the workflow takes longer than the initial visibility timeout.
            renew_task = asyncio.create_task(
                self._renew_visibility_loop(worker_id),
                name=f"queue-renew-{worker_id}",
            )

            # Use the step-based workflow runner (src/steps/claim_processor.py).
            claim_processor = self.app_context.get_service(ClaimProcessor)

            workflow_error: Exception | None = None
            try:
                await claim_processor.run(input_data=claim_process_id)
            except Exception as e:
                workflow_error = e
            finally:
                claim_processor = None

            execution_time = time.time() - message_start_time

            # Cancel the visibility-renewal loop BEFORE touching the queue
            # message.  If the renew loop fires ``update_message`` while we
            # are about to ``delete_message``, the pop_receipt can become
            # stale and the delete silently fails — leaving the message in
            # the queue for duplicate processing.
            if renew_task is not None:
                renew_task.cancel()
                await asyncio.gather(renew_task, return_exceptions=True)
                renew_task = None

            if workflow_error is None:
                await self._handle_successful_processing(
                    queue_message, claim_process_id, execution_time, worker_id=worker_id
                )
            elif isinstance(workflow_error, WorkflowExecutorFailedException):
                await self._handle_failed_no_retry(
                    queue_message,
                    claim_process_id,
                    f"Workflow executor failed: {workflow_error}",
                    execution_time,
                    claim_process_id_for_cleanup=claim_process_id,
                    worker_id=worker_id,
                    force_dead_letter=True,
                )
            else:
                await self._handle_failed_no_retry(
                    queue_message,
                    claim_process_id,
                    f"Unhandled exception: {workflow_error}",
                    execution_time,
                    claim_process_id_for_cleanup=claim_process_id,
                    worker_id=worker_id,
                )

        except asyncio.CancelledError:
            # When cancelled, we assume stop_process has already deleted the message
            # (hard-kill). If it hasn't, the message may become visible again after
            # visibility timeout.
            logger.warning(
                "[worker %s] cancelled while processing process_id=%s message_id=%s",
                worker_id,
                claim_process_id,
                getattr(queue_message, "id", "<unknown>"),
            )
            raise
        except Exception:
            # Last resort: don't let unexpected errors kill the worker.
            execution_time = time.time() - message_start_time
            logger.exception(
                "[worker %s] unexpected error while processing message_id=%s",
                worker_id,
                getattr(queue_message, "id", "<unknown>"),
            )
            try:
                await self._handle_failed_no_retry(
                    queue_message,
                    claim_process_id,
                    "Worker crashed while processing message",
                    execution_time,
                    claim_process_id_for_cleanup=None,
                    worker_id=worker_id,
                )
            except Exception:
                pass
        finally:
            if renew_task is not None:
                renew_task.cancel()
                await asyncio.gather(renew_task, return_exceptions=True)
            self._worker_inflight.pop(worker_id, None)
            self._worker_inflight_message.pop(worker_id, None)
            self._worker_inflight_batch_id.pop(worker_id, None)

    async def _handle_successful_processing(
        self,
        queue_message: QueueMessage,
        claim_process_id: str,
        execution_time: float,
        *,
        worker_id: int | None = None,
    ):
        """Delete the queue message after successful processing.

        Uses the latest ``pop_receipt`` from ``_worker_inflight_message``
        (which may have been updated by the visibility-renewal loop) rather
        than the original ``queue_message.pop_receipt``.

        If the message was already deleted or the visibility timeout expired
        (``ResourceNotFoundError``), the error is logged at DEBUG level and
        silently ignored — the job completed successfully regardless.
        """

        try:
            if self.main_queue:
                message_id = getattr(queue_message, "id", None)
                pop_receipt = getattr(queue_message, "pop_receipt", None)
                if worker_id is not None:
                    tracked = self._worker_inflight_message.get(worker_id)
                    if tracked:
                        message_id, pop_receipt = tracked
                if message_id is not None and pop_receipt is not None:
                    self.main_queue.delete_message(message_id, pop_receipt)

                if self.debug_mode:
                    logger.info(
                        f"The message {queue_message.id} - Successfully processed {claim_process_id} "
                        f"in {execution_time:.2f}s"
                    )

        except ResourceNotFoundError:
            # Message was already deleted or visibility timeout expired - this is okay
            logger.debug(
                f"The message {queue_message.id} already processed "
                f"(visibility timeout expired or processed by another worker)"
            )
        except AzureError as e:
            logger.error(f"Failed to delete processed message: {e}")

    async def _handle_failed_no_retry(
        self,
        queue_message: QueueMessage,
        process_id: str,
        failure_reason: str,
        execution_time: float,
        claim_process_id_for_cleanup: str | None = None,
        cleanup_scope: str = "output",
        *,
        worker_id: int | None = None,
        force_dead_letter: bool = False,
    ):
        """Handle a failed message: retry if attempts remain, otherwise dead-letter and delete.

        Decision tree:
        1. Read ``dequeue_count`` from the message (Azure increments this
           each time the message is received).
        2. If ``force_dead_letter`` is ``True`` **or** ``dequeue_count >=
           max_receive_attempts``:
           a. Send a JSON payload (original content + failure reason +
              metadata) to the dead-letter queue.
           b. If the DLQ send fails, extend the visibility timeout on the
              original message (``max(60, retry_delay_s)``) and **return
              without deleting** — this prevents silent data loss.
           c. Delete output blobs under ``<claim_process_id>/converted/``
              to remove partial / stale artifacts.
           d. Delete the original message from the main queue.
        3. Otherwise (retryable failure):
           a. Shorten the visibility timeout to
              ``retry_visibility_delay_seconds`` so the message becomes
              available to consumers sooner.
           b. Update the tracked ``pop_receipt`` so subsequent operations
              (e.g. ``stop_process``) use the latest receipt.
           c. Return immediately — no blob cleanup, no message deletion.

        Args:
            queue_message: The original Azure ``QueueMessage``.
            process_id: The ``claim_process_id`` (may be ``"<unknown>"`` if
                parsing failed).
            failure_reason: Human-readable failure description.
            execution_time: Wall-clock seconds the job ran before failing.
            claim_process_id_for_cleanup: If set, output blobs under this
                id are deleted on the final attempt.
            cleanup_scope: ``"output"`` (default) or ``"process"``.
            worker_id: Worker that processed the message (used to look up
                the latest ``pop_receipt``).
            force_dead_letter: Skip retry logic and immediately dead-letter
                (used for malformed messages).
        """

        attempt = int(getattr(queue_message, "dequeue_count", 1) or 1)
        max_attempts = max(1, int(getattr(self.config, "max_receive_attempts", 3) or 3))
        retry_delay_s = max(
            0,
            int(getattr(self.config, "retry_visibility_delay_seconds", 5) or 0),
        )

        should_dead_letter = force_dead_letter or (attempt >= max_attempts)

        if not should_dead_letter:
            logger.warning(
                "Job failed (attempt %s/%s). Will retry. process_id=%s message_id=%s reason=%s elapsed=%.2fs",
                attempt,
                max_attempts,
                process_id,
                getattr(queue_message, "id", None),
                failure_reason,
                execution_time,
            )

            # Shorten the wait until the next attempt.
            try:
                if self.main_queue:
                    message_id = getattr(queue_message, "id", None)
                    pop_receipt = getattr(queue_message, "pop_receipt", None)
                    if worker_id is not None:
                        tracked = self._worker_inflight_message.get(worker_id)
                        if tracked:
                            message_id, pop_receipt = tracked

                    if message_id is not None and pop_receipt is not None:
                        receipt = await asyncio.to_thread(
                            self.main_queue.update_message,
                            message_id,
                            pop_receipt,
                            visibility_timeout=retry_delay_s,
                        )
                        new_pop = getattr(receipt, "pop_receipt", None)
                        if new_pop and worker_id is not None:
                            self._worker_inflight_message[worker_id] = (
                                str(message_id),
                                str(new_pop),
                            )
            except Exception:
                logger.exception(
                    "Failed to update message visibility for retry message_id=%s",
                    getattr(queue_message, "id", None),
                )

            # Do not cleanup artifacts until the final attempt.
            return

        logger.error(
            "Job failed (final attempt). Dead-lettering message. process_id=%s message_id=%s reason=%s elapsed=%.2fs",
            process_id,
            queue_message.id,
            failure_reason,
            execution_time,
        )

        # 1) Send to dead-letter queue. If this fails, do NOT delete the original
        #    message to avoid silent loss.
        dlq_sent = False
        try:
            if self.dead_letter_queue:
                payload = {
                    "process_id": process_id,
                    "failure_reason": failure_reason,
                    "attempt": attempt,
                    "max_attempts": max_attempts,
                    "message_id": getattr(queue_message, "id", None),
                    "inserted_on": str(getattr(queue_message, "inserted_on", "") or ""),
                    "original_content": str(
                        getattr(queue_message, "content", "") or ""
                    ),
                }
                await asyncio.to_thread(
                    self.dead_letter_queue.send_message,
                    json.dumps(payload, ensure_ascii=False),
                )
                dlq_sent = True
        except Exception:
            logger.exception(
                "Failed to send message to dead-letter queue; leaving original for retry message_id=%s",
                getattr(queue_message, "id", None),
            )

        if not dlq_sent:
            # Give it a longer delay to avoid a tight failure loop.
            try:
                if self.main_queue:
                    message_id = getattr(queue_message, "id", None)
                    pop_receipt = getattr(queue_message, "pop_receipt", None)
                    if worker_id is not None:
                        tracked = self._worker_inflight_message.get(worker_id)
                        if tracked:
                            message_id, pop_receipt = tracked

                    if message_id is not None and pop_receipt is not None:
                        await asyncio.to_thread(
                            self.main_queue.update_message,
                            message_id,
                            pop_receipt,
                            visibility_timeout=max(60, retry_delay_s),
                        )
            except Exception:
                pass
            return

        # Cleanup:
        # - Default: clear output folder only (avoids stale artifacts while preserving inputs).
        # - Hard termination: clear the entire process folder (includes uploaded resources).
        if claim_process_id_for_cleanup:
            try:
                scope = (cleanup_scope or "output").strip().lower()
                if scope in {"process", "output"}:
                    await self._cleanup_output_blobs(claim_process_id_for_cleanup)
            except Exception:
                logger.exception(
                    "Failed to cleanup blobs (process_id=%s scope=%s)",
                    process_id,
                    cleanup_scope,
                )

        try:
            if self.main_queue:
                message_id = getattr(queue_message, "id", None)
                pop_receipt = getattr(queue_message, "pop_receipt", None)

                # If visibility was renewed, prefer the latest tracked pop_receipt.
                if worker_id is not None:
                    tracked = self._worker_inflight_message.get(worker_id)
                    if tracked:
                        message_id, pop_receipt = tracked

                if message_id is not None and pop_receipt is not None:
                    self.main_queue.delete_message(message_id, pop_receipt)
        except ResourceNotFoundError:
            logger.debug(
                "Failed message already deleted/expired message_id=%s",
                getattr(queue_message, "id", None),
            )
        except AzureError as e:
            logger.error("Failed to delete failed message: %s", e)

    def _build_task_param(self, queue_message: QueueMessage) -> str:
        """Extract ``claim_process_id`` from a queue message payload.

        Delegates to the module-level ``parse_claim_task_parameters_from_queue_content``
        function, which handles both raw JSON and base64-encoded payloads.

        Raises:
            ValueError: If the payload is missing, malformed, or contains an
                empty ``claim_process_id``.
        """

        raw = getattr(queue_message, "content", "")
        if raw is None:
            raise ValueError("Queue message content is empty")

        params = parse_claim_task_parameters_from_queue_content(raw)
        batch_id = (params.claim_process_id or "").strip()
        if not batch_id:
            raise ValueError("claim_process_id is empty")
        return batch_id

    async def _renew_visibility_loop(self, worker_id: int) -> None:
        """Periodically extend the visibility timeout of the in-flight message.

        Runs as a concurrent ``asyncio.Task`` alongside the job.  Every
        ``~60 %`` of the configured ``visibility_timeout_minutes`` it calls
        ``main_queue.update_message`` to push the visibility window forward
        by the full timeout duration.

        The updated ``pop_receipt`` returned by Azure is stored back into
        ``_worker_inflight_message`` so that other operations (message
        deletion, retry visibility shortening) always use the latest receipt.

        Exit conditions:
        - ``is_running`` becomes ``False`` (service shutdown).
        - ``ResourceNotFoundError`` — the message was already deleted.
        - The task is cancelled by ``_process_queue_message``'s ``finally``
          block once the job completes.
        """

        # Renew at ~60% of the visibility timeout.
        visibility_s = max(30, int(self.config.visibility_timeout_minutes * 60))
        sleep_s = max(10, int(visibility_s * 0.6))

        while self.is_running:
            await asyncio.sleep(sleep_s)
            msg = self._worker_inflight_message.get(worker_id)
            if not msg or not self.main_queue:
                continue

            message_id, pop_receipt = msg
            try:
                receipt = await asyncio.to_thread(
                    self.main_queue.update_message,
                    message_id,
                    pop_receipt,
                    visibility_timeout=visibility_s,
                )
                new_pop = getattr(receipt, "pop_receipt", None)
                if new_pop:
                    self._worker_inflight_message[worker_id] = (
                        message_id,
                        str(new_pop),
                    )
            except ResourceNotFoundError:
                # Message already deleted.
                return
            except Exception:
                logger.exception(
                    "[worker %s] failed to renew queue message visibility", worker_id
                )

    async def _ensure_queues_exist(self):
        """Create the main and dead-letter queues if they do not already exist.

        Calls ``QueueClient.create_queue()`` for both the main queue and the
        dead-letter queue.  Azure returns ``409 Conflict`` if the queue
        already exists, which is caught and silently ignored.  Any other
        ``AzureError`` is propagated to the caller.
        """
        try:
            try:
                if not self.main_queue:
                    raise RuntimeError("main_queue is not initialized")
                self.main_queue.create_queue()
                if self.debug_mode:
                    logger.info(f"Created main queue: {self.config.queue_name}")
            except Exception:
                pass  # Ignored — queue likely already exists (409 Conflict)

            try:
                if not self.dead_letter_queue:
                    raise RuntimeError("dead_letter_queue is not initialized")
                self.dead_letter_queue.create_queue()
                if self.debug_mode:
                    logger.info(
                        "Created dead-letter queue: %s",
                        getattr(self.dead_letter_queue, "queue_name", "<unknown>"),
                    )
            except Exception:
                pass  # Ignored — queue likely already exists (409 Conflict)

        except AzureError as e:
            logger.error(f"Failed to ensure queues exist: {e}")
            raise

    def get_service_status(self) -> dict:
        """Return a snapshot of the service's running state and worker info.

        Returns a dict with:
        - ``is_running``: whether the service loop is active.
        - ``active_workers`` / ``active_worker_ids``: count and sorted list
          of workers currently inside ``_worker_loop``.
        - ``inflight``: mapping of ``worker_id → process_id`` for jobs
          currently in progress.
        - ``configured_workers``, ``queue_name``, ``visibility_timeout_minutes``:
          static configuration values for reference.
        """
        return {
            "is_running": self.is_running,
            "active_workers": len(self.active_workers),
            "active_worker_ids": sorted(self.active_workers),
            "inflight": dict(self._worker_inflight),
            "configured_workers": self.config.concurrent_workers,
            "queue_name": self.config.queue_name,
            "visibility_timeout_minutes": self.config.visibility_timeout_minutes,
        }

    async def get_queue_info(self) -> dict:
        """Return approximate message count and queue metadata (debug helper).

        Calls ``main_queue.get_queue_properties()`` and returns:
        - ``main_queue.name``: queue name.
        - ``main_queue.approximate_message_count``: Azure's approximate
          count (may lag by a few seconds).
        - ``main_queue.metadata``: user-defined queue metadata dict.
        - ``visibility_timeout_minutes`` and ``poll_interval_seconds``:
          current configuration values.

        Returns ``{"error": "..."}`` if the queue client is not initialised
        or the call fails.
        """
        try:
            # Get queue properties
            if not self.main_queue:
                return {"error": "main_queue is not initialized"}

            main_queue_props = self.main_queue.get_queue_properties()

            return {
                "main_queue": {
                    "name": self.config.queue_name,
                    "approximate_message_count": main_queue_props.approximate_message_count,
                    "metadata": main_queue_props.metadata,
                },
                "visibility_timeout_minutes": self.config.visibility_timeout_minutes,
                "poll_interval_seconds": self.config.poll_interval_seconds,
            }
        except Exception as e:
            return {"error": f"Failed to get queue info: {e}"}
