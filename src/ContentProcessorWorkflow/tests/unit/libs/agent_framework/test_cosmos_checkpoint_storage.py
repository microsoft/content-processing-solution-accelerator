# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs/agent_framework/cosmos_checkpoint_storage.py."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from libs.agent_framework.cosmos_checkpoint_storage import (
    CosmosCheckpointStorage,
    CosmosWorkflowCheckpoint,
    CosmosWorkflowCheckpointRepository,
)


# ── CosmosWorkflowCheckpoint ────────────────────────────────────────────────


class TestCosmosWorkflowCheckpoint:
    def test_id_derived_from_checkpoint_id(self):
        cp = CosmosWorkflowCheckpoint(checkpoint_id="ckpt-1", workflow_id="wf-1")
        assert cp.id == "ckpt-1"

    def test_defaults(self):
        cp = CosmosWorkflowCheckpoint(checkpoint_id="ckpt-1")
        assert cp.workflow_id == ""
        assert cp.timestamp == ""
        assert cp.messages == {}
        assert cp.shared_state == {}
        assert cp.iteration_count == 0
        assert cp.metadata == {}
        assert cp.version == "1.0"


# ── CosmosCheckpointStorage (adapter) ────────────────────────────────────────


class TestCosmosCheckpointStorage:
    def _make_storage(self):
        repo = MagicMock(spec=CosmosWorkflowCheckpointRepository)
        repo.save_checkpoint = AsyncMock()
        repo.load_checkpoint = AsyncMock()
        repo.list_checkpoint_ids = AsyncMock(return_value=["c1", "c2"])
        repo.list_checkpoints = AsyncMock(return_value=[])
        repo.delete_checkpoint = AsyncMock()
        return CosmosCheckpointStorage(repository=repo), repo

    def test_save_delegates_to_repository(self):
        async def _run():
            storage, repo = self._make_storage()

            checkpoint = MagicMock()
            checkpoint.to_dict.return_value = {
                "checkpoint_id": "ckpt-1",
                "workflow_id": "wf-1",
            }

            await storage.save_checkpoint(checkpoint)
            repo.save_checkpoint.assert_awaited_once()

        asyncio.run(_run())

    def test_load_delegates_to_repository(self):
        async def _run():
            storage, repo = self._make_storage()
            fake_cp = CosmosWorkflowCheckpoint(checkpoint_id="ckpt-1")
            repo.load_checkpoint.return_value = fake_cp

            result = await storage.load_checkpoint("ckpt-1")
            assert result is fake_cp
            repo.load_checkpoint.assert_awaited_once_with("ckpt-1")

        asyncio.run(_run())

    def test_list_checkpoint_ids(self):
        async def _run():
            storage, repo = self._make_storage()
            ids = await storage.list_checkpoint_ids(workflow_id="wf-1")
            assert ids == ["c1", "c2"]
            repo.list_checkpoint_ids.assert_awaited_once_with("wf-1")

        asyncio.run(_run())

    def test_delete_delegates_to_repository(self):
        async def _run():
            storage, repo = self._make_storage()
            await storage.delete_checkpoint("ckpt-1")
            repo.delete_checkpoint.assert_awaited_once_with("ckpt-1")

        asyncio.run(_run())
