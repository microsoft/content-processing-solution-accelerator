# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs/agent_framework/mem0_async_memory.py."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from libs.agent_framework.mem0_async_memory import Mem0AsyncMemoryManager


class TestMem0AsyncMemoryManager:
    def test_initial_state_is_none(self):
        mgr = Mem0AsyncMemoryManager()
        assert mgr._memory_instance is None

    @patch("libs.agent_framework.mem0_async_memory.AsyncMemory")
    def test_get_memory_creates_on_first_call(self, mock_async_memory_cls):
        async def _run():
            fake_memory = object()
            mock_async_memory_cls.from_config = AsyncMock(return_value=fake_memory)

            mgr = Mem0AsyncMemoryManager()
            result = await mgr.get_memory()

            assert result is fake_memory
            mock_async_memory_cls.from_config.assert_awaited_once()

        asyncio.run(_run())

    @patch("libs.agent_framework.mem0_async_memory.AsyncMemory")
    def test_get_memory_caches_instance(self, mock_async_memory_cls):
        async def _run():
            fake_memory = object()
            mock_async_memory_cls.from_config = AsyncMock(return_value=fake_memory)

            mgr = Mem0AsyncMemoryManager()
            first = await mgr.get_memory()
            second = await mgr.get_memory()

            assert first is second
            # from_config should be called only once
            assert mock_async_memory_cls.from_config.await_count == 1

        asyncio.run(_run())
