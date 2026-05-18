# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
from __future__ import annotations

"""Unit tests for QueueService stop-process flow."""

import asyncio

import pytest

from services.queue_service import ClaimProcessingQueueService


class _FakeQueue:
    def __init__(self):
        self.deleted: list[tuple[str, str]] = []

    def delete_message(self, message_id: str, pop_receipt: str):
        self.deleted.append((message_id, pop_receipt))


@pytest.mark.parametrize("has_task_param", [True, False])
def test_stop_process_deletes_queue_and_cleans_blobs_and_cancels_job(
    has_task_param: bool,
):
    async def _run():
        service = ClaimProcessingQueueService.__new__(ClaimProcessingQueueService)
        service.app_context = None
        service.main_queue = _FakeQueue()

        # stub out blob cleanup to avoid threads/Azure
        cleaned: list[str] = []

        async def _cleanup_output_blobs(batch_process_id: str):
            cleaned.append(batch_process_id)

        service._cleanup_output_blobs = _cleanup_output_blobs  # type: ignore[attr-defined]

        # minimal inflight tracking
        service._worker_inflight = {1: "p1"}
        service._worker_inflight_message = {1: ("m1", "r1")}
        service._worker_inflight_batch_id = {1: "p1"} if has_task_param else {}

        # in-flight job task should be cancelled by stop_process
        job_task = asyncio.create_task(asyncio.sleep(3600))
        service._worker_inflight_task = {1: job_task}

        ok = await service.stop_process("p1", timeout_seconds=0.1)
        assert ok is True

        # queue message deleted
        assert service.main_queue.deleted == [("m1", "r1")]

        # output cleanup invoked only when batch id is tracked
        if has_task_param:
            assert cleaned == ["p1"]
        else:
            assert cleaned == []

        # job cancelled
        await asyncio.sleep(0)  # allow cancellation to propagate
        assert job_task.cancelled() is True

    asyncio.run(_run())
