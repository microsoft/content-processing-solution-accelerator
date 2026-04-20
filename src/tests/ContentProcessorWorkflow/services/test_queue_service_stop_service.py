# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
from __future__ import annotations

"""Unit tests for QueueService stop-service flow."""

import asyncio

from services.queue_service import ClaimProcessingQueueService


class _FakeClosable:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def test_stop_service_cancels_worker_and_inflight_job_tasks():
    async def _run():
        service = ClaimProcessingQueueService.__new__(ClaimProcessingQueueService)

        # minimal instance metadata
        service.instance_id = 1
        ClaimProcessingQueueService._active_instances.add(service.instance_id)

        service.is_running = True
        service._worker_inflight = {1: "p1"}
        service._worker_inflight_message = {1: ("m1", "r1")}
        service._worker_inflight_batch_id = {1: "p1"}

        # one worker task and one in-flight job task
        worker_task = asyncio.create_task(asyncio.sleep(3600))
        job_task = asyncio.create_task(asyncio.sleep(3600))
        service._worker_tasks = {1: worker_task}
        service._worker_inflight_task = {1: job_task}

        # queue clients are best-effort closable
        service.main_queue = _FakeClosable()
        service.dead_letter_queue = _FakeClosable()
        service.queue_service = _FakeClosable()

        await service.stop_service()

        await asyncio.sleep(0)
        assert worker_task.cancelled() is True
        assert job_task.cancelled() is True
        assert service.is_running is False
        assert service.main_queue.closed is True
        assert service.dead_letter_queue.closed is True
        assert service.queue_service.closed is True

    asyncio.run(_run())
