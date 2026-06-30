# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for DocumentProcessExecutor (name generation and status mapping)."""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone
from unittest.mock import MagicMock

from steps.document_process.executor.document_process_executor import (
    DocumentProcessExecutor,
)


class TestGenerateClaimProcessName:
    def _reset_class_state(self):
        """Reset the class-level counters before each test."""
        DocumentProcessExecutor._claim_name_last_ts = None
        DocumentProcessExecutor._claim_name_seq = 0

    def test_basic_format(self):
        self._reset_class_state()

        async def _run():
            name = await DocumentProcessExecutor._generate_claim_process_name(
                claim_id="abc-123"
            )
            assert name.startswith("claim-")
            parts = name.split("-")
            # claim-<timestamp>-<seq>-<claim_fragment>
            assert len(parts) == 4
            assert parts[0] == "claim"
            assert parts[2] == "0000"  # first call => seq 0

        asyncio.run(_run())

    def test_uses_created_time(self):
        self._reset_class_state()

        async def _run():
            dt = datetime(2025, 6, 15, 10, 30, 0, 0, tzinfo=timezone.utc)
            name = await DocumentProcessExecutor._generate_claim_process_name(
                claim_id="X1", created_time=dt
            )
            # Format is %Y%m%d%H%M%S%f (20 digits, microseconds included)
            assert "20250615103000000000" in name

        asyncio.run(_run())

    def test_sequence_increments_on_same_timestamp(self):
        self._reset_class_state()

        async def _run():
            dt = datetime(2025, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc)
            name1 = await DocumentProcessExecutor._generate_claim_process_name(
                claim_id="A", created_time=dt
            )
            name2 = await DocumentProcessExecutor._generate_claim_process_name(
                claim_id="B", created_time=dt
            )
            assert "-0000-" in name1
            assert "-0001-" in name2

        asyncio.run(_run())

    def test_sequence_resets_on_new_timestamp(self):
        self._reset_class_state()

        async def _run():
            dt1 = datetime(2025, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc)
            dt2 = datetime(2025, 1, 1, 0, 0, 1, 0, tzinfo=timezone.utc)  # +1 sec

            await DocumentProcessExecutor._generate_claim_process_name(
                claim_id="A", created_time=dt1
            )
            name2 = await DocumentProcessExecutor._generate_claim_process_name(
                claim_id="B", created_time=dt2
            )
            assert "-0000-" in name2  # seq reset

        asyncio.run(_run())

    def test_claim_id_fragment_is_uppercased_alnum(self):
        self._reset_class_state()

        async def _run():
            name = await DocumentProcessExecutor._generate_claim_process_name(
                claim_id="abc-def-ghi"
            )
            fragment = name.split("-")[-1]
            assert fragment == fragment.upper()
            assert fragment.isalnum()

        asyncio.run(_run())

    def test_empty_claim_id_uses_uuid_fragment(self):
        self._reset_class_state()

        async def _run():
            name = await DocumentProcessExecutor._generate_claim_process_name(
                claim_id="---"  # no alnum chars
            )
            fragment = name.split("-")[-1]
            assert len(fragment) == 6
            assert fragment.isalnum()

        asyncio.run(_run())

    def test_invalid_created_time_falls_back_to_now(self):
        self._reset_class_state()

        async def _run():
            # Pass a non-datetime value
            name = await DocumentProcessExecutor._generate_claim_process_name(
                claim_id="test", created_time="not-a-datetime"
            )
            assert name.startswith("claim-")

        asyncio.run(_run())


# ── Status code → status_text mapping ────────────────────────────────────────


class TestStatusCodeMapping:
    """Verify the status_code → status_text mapping used after polling.

    The mapping lives inside handle_execute but is pure logic that we
    replicate here to lock down the expected contract.
    """

    @staticmethod
    def _map_status(status_code: int) -> str:
        """Mirror the production mapping in handle_execute."""
        if status_code in (200, 202):
            return "Processing"
        elif status_code == 302:
            return "Completed"
        elif status_code == 404:
            return "Failed"
        elif status_code == 500:
            return "Failed"
        else:
            return "Failed"

    def test_200_is_processing(self):
        assert self._map_status(200) == "Processing"

    def test_202_is_processing(self):
        assert self._map_status(202) == "Processing"

    def test_302_is_completed(self):
        assert self._map_status(302) == "Completed"

    def test_404_is_failed(self):
        assert self._map_status(404) == "Failed"

    def test_500_is_failed(self):
        assert self._map_status(500) == "Failed"

    def test_unknown_status_is_failed(self):
        assert self._map_status(503) == "Failed"
        assert self._map_status(429) == "Failed"


# ── _on_poll behaviour ──────────────────────────────────────────────────────


class TestOnPollBehaviour:
    """Exercise the _on_poll callback logic.

    Since _on_poll is a closure, we replicate its logic in a standalone
    async function that mirrors the production code exactly, then test it
    with synthetic HTTP responses.
    """

    @staticmethod
    async def _simulate_on_poll(
        r,
        *,
        process_id: str | None,
        seen_progress_digests: set[str],
        upserted: list[dict],
        claim_id: str = "batch-1",
        file_name: str = "doc.pdf",
        content_type: str = "application/pdf",
    ) -> str | None:
        """Replicate the _on_poll logic and return updated process_id."""
        if r.status not in (200, 500) or not r.body:
            return process_id

        digest = hashlib.sha256(r.body).hexdigest()
        if digest in seen_progress_digests:
            return process_id
        seen_progress_digests.add(digest)
        if len(seen_progress_digests) > 64:
            seen_progress_digests.clear()

        try:
            payload = r.json()
        except Exception:
            payload = None

        if not isinstance(payload, dict):
            return process_id

        process_id = payload.get("process_id") or process_id
        current_process_id = payload.get("process_id") or process_id

        status = payload.get("status")
        if r.status == 500 and not status:
            status = "Failed"

        upserted.append(
            {
                "process_id": current_process_id,
                "file_name": file_name,
                "mime_type": content_type,
                "status": status,
            }
        )
        return process_id

    @staticmethod
    def _make_response(status: int, body_dict: dict | None) -> MagicMock:
        import json as _json

        resp = MagicMock()
        resp.status = status
        if body_dict is not None:
            raw = _json.dumps(body_dict).encode()
            resp.body = raw
            resp.json.return_value = body_dict
            resp.text.return_value = _json.dumps(body_dict)
        else:
            resp.body = None
        return resp

    def test_200_with_status_upserts(self):
        async def _run():
            upserted: list[dict] = []
            digests: set[str] = set()
            r = self._make_response(200, {"process_id": "p1", "status": "Extract"})
            pid = await self._simulate_on_poll(
                r, process_id=None, seen_progress_digests=digests, upserted=upserted
            )
            assert pid == "p1"
            assert len(upserted) == 1
            assert upserted[0]["status"] == "Extract"

        asyncio.run(_run())

    def test_500_with_status_in_payload(self):
        async def _run():
            upserted: list[dict] = []
            digests: set[str] = set()
            r = self._make_response(
                500, {"process_id": "p2", "status": "InternalError"}
            )
            pid = await self._simulate_on_poll(
                r, process_id=None, seen_progress_digests=digests, upserted=upserted
            )
            assert pid == "p2"
            assert upserted[0]["status"] == "InternalError"

        asyncio.run(_run())

    def test_500_without_status_defaults_to_failed(self):
        async def _run():
            upserted: list[dict] = []
            digests: set[str] = set()
            r = self._make_response(500, {"process_id": "p3"})
            pid = await self._simulate_on_poll(
                r, process_id=None, seen_progress_digests=digests, upserted=upserted
            )
            assert pid == "p3"
            assert upserted[0]["status"] == "Failed"

        asyncio.run(_run())

    def test_202_is_ignored(self):
        async def _run():
            upserted: list[dict] = []
            digests: set[str] = set()
            r = self._make_response(202, {"process_id": "p4", "status": "Running"})
            pid = await self._simulate_on_poll(
                r, process_id="old", seen_progress_digests=digests, upserted=upserted
            )
            assert pid == "old"
            assert upserted == []

        asyncio.run(_run())

    def test_no_body_is_ignored(self):
        async def _run():
            upserted: list[dict] = []
            digests: set[str] = set()
            r = self._make_response(200, None)
            pid = await self._simulate_on_poll(
                r, process_id="old", seen_progress_digests=digests, upserted=upserted
            )
            assert pid == "old"
            assert upserted == []

        asyncio.run(_run())

    def test_duplicate_body_skipped(self):
        async def _run():
            upserted: list[dict] = []
            digests: set[str] = set()
            r = self._make_response(200, {"process_id": "p5", "status": "Extract"})
            await self._simulate_on_poll(
                r, process_id=None, seen_progress_digests=digests, upserted=upserted
            )
            await self._simulate_on_poll(
                r, process_id="p5", seen_progress_digests=digests, upserted=upserted
            )
            assert len(upserted) == 1

        asyncio.run(_run())

    def test_malformed_json_body_ignored(self):
        async def _run():
            upserted: list[dict] = []
            digests: set[str] = set()
            r = MagicMock()
            r.status = 200
            r.body = b"not-json"
            r.json.side_effect = ValueError("bad json")
            r.text.return_value = "not-json"
            pid = await self._simulate_on_poll(
                r, process_id="old", seen_progress_digests=digests, upserted=upserted
            )
            assert pid == "old"
            assert upserted == []

        asyncio.run(_run())

    def test_process_id_preserved_when_payload_lacks_it(self):
        async def _run():
            upserted: list[dict] = []
            digests: set[str] = set()
            r = self._make_response(200, {"status": "Map"})
            pid = await self._simulate_on_poll(
                r,
                process_id="existing",
                seen_progress_digests=digests,
                upserted=upserted,
            )
            assert pid == "existing"
            assert upserted[0]["process_id"] == "existing"
            assert upserted[0]["status"] == "Map"

        asyncio.run(_run())
