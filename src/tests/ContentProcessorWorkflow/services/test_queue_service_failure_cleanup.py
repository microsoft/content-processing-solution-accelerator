# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
from __future__ import annotations

"""Unit tests for QueueService failure cleanup."""

import asyncio

import pytest

from services.queue_service import ClaimProcessingQueueService


class _Cfg:
    def __init__(
        self, max_receive_attempts: int = 1, retry_visibility_delay_seconds: int = 0
    ):
        self.max_receive_attempts = max_receive_attempts
        self.retry_visibility_delay_seconds = retry_visibility_delay_seconds


class _FakeQueue:
    def __init__(self):
        self.deleted: list[tuple[str, str]] = []

    def delete_message(self, message_id: str, pop_receipt: str):
        self.deleted.append((message_id, pop_receipt))

    def update_message(
        self, message_id: str, pop_receipt: str, *, visibility_timeout: int
    ):
        # return an object with pop_receipt (mirrors SDK shape enough for tests)
        class _Receipt:
            def __init__(self, pop_receipt: str):
                self.pop_receipt = pop_receipt

        return _Receipt(pop_receipt)


class _FakeDLQ:
    def __init__(self):
        self.sent: list[str] = []

    def send_message(self, content: str):
        self.sent.append(content)


class _FakeQueueMessage:
    def __init__(
        self,
        message_id: str = "m1",
        pop_receipt: str = "r1",
        dequeue_count: int = 1,
        content: str = '{"batch_process_id": "p1"}',
    ):
        self.id = message_id
        self.pop_receipt = pop_receipt
        self.dequeue_count = dequeue_count
        self.content = content
        self.inserted_on = None


@pytest.mark.parametrize("pass_batch_id", [True, False])
def test_failed_no_retry_cleans_output_on_final_attempt_when_batch_id_available(
    pass_batch_id: bool,
):
    async def _run():
        service = ClaimProcessingQueueService.__new__(ClaimProcessingQueueService)
        service.app_context = None
        service.main_queue = _FakeQueue()
        service.dead_letter_queue = _FakeDLQ()
        service.config = _Cfg(max_receive_attempts=1, retry_visibility_delay_seconds=0)

        called: list[str] = []

        async def _cleanup_output_blobs(batch_process_id: str):
            called.append(batch_process_id)

        service._cleanup_output_blobs = _cleanup_output_blobs  # type: ignore[attr-defined]

        batch_id = "p1" if pass_batch_id else None

        await service._handle_failed_no_retry(
            queue_message=_FakeQueueMessage(),
            process_id="p1",
            failure_reason="boom",
            execution_time=1.23,
            claim_process_id_for_cleanup=batch_id,
        )

        assert service.main_queue.deleted == [("m1", "r1")]
        if pass_batch_id:
            assert called == ["p1"]
        else:
            assert called == []

    asyncio.run(_run())


def test_workflow_executor_failed_sends_to_dlq_with_force_dead_letter():
    """WorkflowExecutorFailedException triggers force_dead_letter=True,
    so the message goes straight to the DLQ regardless of dequeue_count."""

    async def _run():
        service = ClaimProcessingQueueService.__new__(ClaimProcessingQueueService)
        service.app_context = None
        service.main_queue = _FakeQueue()
        service.dead_letter_queue = _FakeDLQ()
        service.config = _Cfg(max_receive_attempts=5, retry_visibility_delay_seconds=0)
        service._worker_inflight_message = {}

        cleaned: list[str] = []

        async def _cleanup_output_blobs(batch_process_id: str):
            cleaned.append(batch_process_id)

        service._cleanup_output_blobs = _cleanup_output_blobs  # type: ignore[attr-defined]

        # dequeue_count=1, meaning first attempt, but force_dead_letter
        # should bypass the retry logic
        msg = _FakeQueueMessage(dequeue_count=1)

        await service._handle_failed_no_retry(
            queue_message=msg,
            process_id="p1",
            failure_reason="Workflow executor failed: RAI unsafe",
            execution_time=2.0,
            claim_process_id_for_cleanup="p1",
            force_dead_letter=True,
        )

        # Message was sent to DLQ
        assert len(service.dead_letter_queue.sent) == 1
        assert "RAI unsafe" in service.dead_letter_queue.sent[0]

        # Message was deleted from main queue
        assert service.main_queue.deleted == [("m1", "r1")]

        # Output blobs cleaned up
        assert cleaned == ["p1"]

    asyncio.run(_run())


def test_retry_when_not_final_attempt():
    """Non-final attempts should NOT dead-letter; message stays for retry."""

    async def _run():
        service = ClaimProcessingQueueService.__new__(ClaimProcessingQueueService)
        service.app_context = None
        service.main_queue = _FakeQueue()
        service.dead_letter_queue = _FakeDLQ()
        service.config = _Cfg(max_receive_attempts=3, retry_visibility_delay_seconds=5)
        service._worker_inflight_message = {}

        cleaned: list[str] = []

        async def _cleanup_output_blobs(batch_process_id: str):
            cleaned.append(batch_process_id)

        service._cleanup_output_blobs = _cleanup_output_blobs  # type: ignore[attr-defined]

        # First attempt out of 3 — should retry, not dead-letter
        msg = _FakeQueueMessage(dequeue_count=1)

        await service._handle_failed_no_retry(
            queue_message=msg,
            process_id="p1",
            failure_reason="Transient error",
            execution_time=1.0,
            claim_process_id_for_cleanup="p1",
        )

        # NOT sent to DLQ
        assert len(service.dead_letter_queue.sent) == 0

        # NOT deleted from main queue
        assert service.main_queue.deleted == []

        # NOT cleaned up
        assert cleaned == []

    asyncio.run(_run())
