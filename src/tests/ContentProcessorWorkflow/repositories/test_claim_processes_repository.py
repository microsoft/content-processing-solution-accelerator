# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for the Claim_Processes repository (async CRUD operations).

All Cosmos DB I/O is mocked via ``AsyncMock`` patches on the
``RepositoryBase`` methods that ``Claim_Processes`` delegates to.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from repositories.claim_processes import Claim_Processes
from repositories.model.claim_process import (
    Claim_Process,
    Claim_Steps,
    Content_Process,
)


def _make_repo() -> Claim_Processes:
    """Create a Claim_Processes instance without a real Cosmos connection."""
    with patch.object(Claim_Processes, "__init__", lambda self, *a, **kw: None):
        repo = Claim_Processes.__new__(Claim_Processes)
    return repo


def _make_claim(process_id: str = "p1", **overrides) -> Claim_Process:
    defaults = dict(id=process_id, schemaset_id="ss1")
    defaults.update(overrides)
    return Claim_Process(**defaults)


# ── Create_Claim_Process ─────────────────────────────────────────────────────


class TestCreateClaimProcess:
    def test_creates_new_when_none_exists(self):
        async def _run():
            repo = _make_repo()
            repo.get_async = AsyncMock(return_value=None)
            repo.delete_async = AsyncMock()
            repo.add_async = AsyncMock()

            claim = _make_claim()
            result = await repo.Create_Claim_Process(claim)

            repo.get_async.assert_awaited_once_with("p1")
            repo.delete_async.assert_not_awaited()
            repo.add_async.assert_awaited_once_with(claim)
            assert result is claim

        asyncio.run(_run())

    def test_replaces_existing(self):
        async def _run():
            repo = _make_repo()
            existing = _make_claim()
            repo.get_async = AsyncMock(return_value=existing)
            repo.delete_async = AsyncMock()
            repo.add_async = AsyncMock()

            new_claim = _make_claim()
            result = await repo.Create_Claim_Process(new_claim)

            repo.delete_async.assert_awaited_once_with("p1")
            repo.add_async.assert_awaited_once_with(new_claim)
            assert result is new_claim

        asyncio.run(_run())


# ── Upsert_Content_Process ───────────────────────────────────────────────────


class TestUpsertContentProcess:
    def test_appends_new_content_process(self):
        async def _run():
            repo = _make_repo()
            claim = _make_claim()
            repo.get_async = AsyncMock(return_value=claim)
            repo.update_async = AsyncMock()

            cp = Content_Process(process_id="p1", file_name="new.pdf")
            result = await repo.Upsert_Content_Process("p1", cp)

            assert result is not None
            assert len(result.processed_documents) == 1
            assert result.processed_documents[0].file_name == "new.pdf"

        asyncio.run(_run())

    def test_replaces_existing_content_process(self):
        async def _run():
            repo = _make_repo()
            old_cp = Content_Process(
                process_id="p1", file_name="doc.pdf", entity_score=0.5
            )
            claim = _make_claim(processed_documents=[old_cp])
            repo.get_async = AsyncMock(return_value=claim)
            repo.update_async = AsyncMock()

            new_cp = Content_Process(
                process_id="p1", file_name="doc.pdf", entity_score=0.9
            )
            result = await repo.Upsert_Content_Process("p1", new_cp)

            assert result is not None
            assert len(result.processed_documents) == 1
            assert result.processed_documents[0].entity_score == 0.9

        asyncio.run(_run())

    def test_returns_none_when_claim_not_found(self):
        async def _run():
            repo = _make_repo()
            repo.get_async = AsyncMock(return_value=None)

            cp = Content_Process(process_id="p1", file_name="x.pdf")
            result = await repo.Upsert_Content_Process("missing", cp)

            assert result is None

        asyncio.run(_run())


# ── Update helpers ───────────────────────────────────────────────────────────


class TestUpdateHelpers:
    def test_update_summary(self):
        async def _run():
            repo = _make_repo()
            claim = _make_claim()
            repo.get_async = AsyncMock(return_value=claim)
            repo.update_async = AsyncMock()

            result = await repo.Update_Claim_Process_Summary("p1", "new summary")
            assert result is not None
            assert result.process_summary == "new summary"

        asyncio.run(_run())

    def test_update_summary_returns_none_when_missing(self):
        async def _run():
            repo = _make_repo()
            repo.get_async = AsyncMock(return_value=None)
            result = await repo.Update_Claim_Process_Summary("x", "s")
            assert result is None

        asyncio.run(_run())

    def test_update_gaps(self):
        async def _run():
            repo = _make_repo()
            claim = _make_claim()
            repo.get_async = AsyncMock(return_value=claim)
            repo.update_async = AsyncMock()

            result = await repo.Update_Claim_Process_Gaps("p1", "gap text")
            assert result is not None
            assert result.process_gaps == "gap text"

        asyncio.run(_run())

    def test_update_comment(self):
        async def _run():
            repo = _make_repo()
            claim = _make_claim()
            repo.get_async = AsyncMock(return_value=claim)
            repo.update_async = AsyncMock()

            result = await repo.Update_Claim_Process_Comment("p1", "specialist note")
            assert result is not None
            assert result.process_comment == "specialist note"

        asyncio.run(_run())

    def test_update_status(self):
        async def _run():
            repo = _make_repo()
            claim = _make_claim()
            repo.get_async = AsyncMock(return_value=claim)
            repo.update_async = AsyncMock()

            result = await repo.Update_Claim_Process_Status(
                "p1", Claim_Steps.COMPLETED
            )
            assert result is not None
            assert result.status == Claim_Steps.COMPLETED

        asyncio.run(_run())

    def test_update_content_process_status_replaces_list(self):
        async def _run():
            repo = _make_repo()
            claim = _make_claim()
            repo.get_async = AsyncMock(return_value=claim)
            repo.update_async = AsyncMock()

            new_docs = [Content_Process(process_id="p1", file_name="a.pdf")]
            result = await repo.Update_Claim_Content_Process_Status("p1", new_docs)
            assert result is not None
            assert len(result.processed_documents) == 1

        asyncio.run(_run())


# ── Delete ───────────────────────────────────────────────────────────────────


class TestDeleteClaimProcess:
    def test_delete(self):
        async def _run():
            repo = _make_repo()
            repo.delete_async = AsyncMock()
            await repo.Delete_Claim_Process("p1")
            repo.delete_async.assert_awaited_once_with("p1")

        asyncio.run(_run())
