# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for services.content_process_service (direct resource access)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from services.content_process_service import ContentProcessService


def _make_service() -> ContentProcessService:
    """Build a ContentProcessService with mocked dependencies."""
    config = MagicMock()
    config.app_cosmos_connstr = "mongodb://fake"
    config.app_cosmos_database = "testdb"
    config.app_cosmos_container_process = "Processes"
    config.app_storage_account_name = "fakestorage"
    config.app_storage_queue_url = "https://fakestorage.queue.core.windows.net/"
    config.app_message_queue_extract = "extract-queue"
    config.app_cps_processes = "cps-processes"

    credential = MagicMock()

    with patch.object(ContentProcessService, "__init__", lambda self, *a, **kw: None):
        svc = ContentProcessService.__new__(ContentProcessService)
        svc._config = config
        svc._credential = credential
        svc._blob_helper = None
        svc._queue_client = None
        svc._process_repo = AsyncMock()

    return svc


# ── get_status ──────────────────────────────────────────────────────────


class TestGetStatus:
    def test_returns_none_when_not_found(self):
        async def _run():
            svc = _make_service()
            svc._process_repo.get_async.return_value = None
            result = await svc.get_status("missing-id")
            assert result is None

        asyncio.run(_run())

    def test_returns_status_dict(self):
        async def _run():
            svc = _make_service()
            record = MagicMock()
            record.status = "extract"
            record.processed_file_name = "test.pdf"
            svc._process_repo.get_async.return_value = record

            result = await svc.get_status("p1")
            assert result == {
                "status": "extract",
                "process_id": "p1",
                "file_name": "test.pdf",
            }

        asyncio.run(_run())

    def test_defaults_to_processing_when_status_none(self):
        async def _run():
            svc = _make_service()
            record = MagicMock()
            record.status = None
            record.processed_file_name = ""
            svc._process_repo.get_async.return_value = record

            result = await svc.get_status("p1")
            assert result["status"] == "processing"

        asyncio.run(_run())


# ── get_processed ───────────────────────────────────────────────────────


class TestGetProcessed:
    def test_returns_none_when_not_found(self):
        async def _run():
            svc = _make_service()
            svc._process_repo.get_async.return_value = None
            result = await svc.get_processed("missing-id")
            assert result is None

        asyncio.run(_run())

    def test_returns_model_dump(self):
        async def _run():
            svc = _make_service()
            record = MagicMock()
            record.model_dump.return_value = {"id": "p1", "status": "Completed"}
            svc._process_repo.get_async.return_value = record

            result = await svc.get_processed("p1")
            assert result == {"id": "p1", "status": "Completed"}

        asyncio.run(_run())


# ── poll_status ─────────────────────────────────────────────────────────


class TestPollStatus:
    def test_returns_failed_when_record_not_found(self):
        async def _run():
            svc = _make_service()
            svc._process_repo.get_async.return_value = None

            result = await svc.poll_status("p1", poll_interval_seconds=0.01)
            assert result["status"] == "Failed"
            assert result["terminal"] is True

        asyncio.run(_run())

    def test_returns_on_completed(self):
        async def _run():
            svc = _make_service()
            record = MagicMock()
            record.status = "Completed"
            record.processed_file_name = "test.pdf"
            svc._process_repo.get_async.return_value = record

            result = await svc.poll_status("p1", poll_interval_seconds=0.01)
            assert result["status"] == "Completed"
            assert result["terminal"] is True

        asyncio.run(_run())

    def test_returns_on_error(self):
        async def _run():
            svc = _make_service()
            record = MagicMock()
            record.status = "Error"
            record.processed_file_name = "test.pdf"
            svc._process_repo.get_async.return_value = record

            result = await svc.poll_status(
                "p1",
                poll_interval_seconds=0.01,
                error_confirmation_polls=3,
            )
            assert result["status"] == "Error"
            assert result["terminal"] is True
            # Should have been called 1 (initial) + 3 (confirmation) = 4 times
            assert svc._process_repo.get_async.call_count == 4

        asyncio.run(_run())

    def test_error_recovers_to_retrying(self):
        """When Error is seen but status changes to Retrying, polling continues."""

        async def _run():
            svc = _make_service()
            # Error -> Retrying -> extract -> Completed
            statuses = iter(["Error", "Retrying", "extract", "Completed"])

            async def _get_async(pid):
                s = next(statuses)
                rec = MagicMock()
                rec.status = s
                rec.processed_file_name = "test.pdf"
                return rec

            svc._process_repo.get_async.side_effect = _get_async

            result = await svc.poll_status(
                "p1",
                poll_interval_seconds=0.01,
                error_confirmation_polls=3,
            )
            assert result["status"] == "Completed"
            assert result["terminal"] is True

        asyncio.run(_run())

    def test_error_recovers_to_step_name(self):
        """When Error is seen but status changes to a step name, polling continues."""

        async def _run():
            svc = _make_service()
            # Error -> map (retry started) -> Completed
            statuses = iter(["Error", "map", "Completed"])

            async def _get_async(pid):
                s = next(statuses)
                rec = MagicMock()
                rec.status = s
                rec.processed_file_name = "test.pdf"
                return rec

            svc._process_repo.get_async.side_effect = _get_async

            result = await svc.poll_status(
                "p1",
                poll_interval_seconds=0.01,
                error_confirmation_polls=3,
            )
            assert result["status"] == "Completed"
            assert result["terminal"] is True

        asyncio.run(_run())

    def test_timeout_returns_last_status(self):
        async def _run():
            svc = _make_service()
            record = MagicMock()
            record.status = "extract"
            record.processed_file_name = "test.pdf"
            svc._process_repo.get_async.return_value = record

            result = await svc.poll_status(
                "p1", poll_interval_seconds=0.01, timeout_seconds=0.03
            )
            assert result["status"] == "extract"
            assert result["terminal"] is True

        asyncio.run(_run())

    def test_on_status_change_callback_invoked(self):
        async def _run():
            svc = _make_service()
            statuses = iter(["processing", "extract", "Completed"])

            async def _get_async(pid):
                s = next(statuses)
                rec = MagicMock()
                rec.status = s
                rec.processed_file_name = "test.pdf"
                return rec

            svc._process_repo.get_async.side_effect = _get_async

            result = await svc.poll_status(
                "p1",
                poll_interval_seconds=0.01,
            )
            assert result["status"] == "Completed"
            assert result["terminal"] is True

        asyncio.run(_run())


# ── close ───────────────────────────────────────────────────────────────


class TestClose:
    def test_releases_resources(self):
        svc = _make_service()
        svc._blob_helper = MagicMock()

        svc.close()

        assert svc._blob_helper is None

    def test_close_idempotent(self):
        svc = _make_service()
        svc._queue_client = None
        svc._blob_helper = None
        svc.close()
        assert svc._blob_helper is None
        assert svc._queue_client is None
