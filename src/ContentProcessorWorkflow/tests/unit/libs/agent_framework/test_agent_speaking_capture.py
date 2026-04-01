# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs/agent_framework/agent_speaking_capture.py."""

from __future__ import annotations

import asyncio
from datetime import datetime
from types import SimpleNamespace

from libs.agent_framework.agent_speaking_capture import (
    AgentSpeakingCaptureMiddleware,
)


def _make_context(
    agent_name: str = "TestAgent",
    is_streaming: bool = False,
    result_text: str = "Hello",
):
    """Build a minimal AgentRunContext-like namespace."""
    agent = SimpleNamespace(name=agent_name)
    result_msg = SimpleNamespace(text=result_text)
    result = SimpleNamespace(messages=[result_msg], text=result_text)
    return SimpleNamespace(
        agent=agent,
        is_streaming=is_streaming,
        result=result,
        messages=[],
    )


# ── Storage ──────────────────────────────────────────────────────────────────


class TestStorage:
    def test_captures_non_streaming_response(self):
        async def _run():
            mw = AgentSpeakingCaptureMiddleware()
            ctx = _make_context(result_text="answer")

            async def _next(_ctx):
                pass

            await mw.process(ctx, _next)

            assert len(mw.captured_responses) == 1
            cap = mw.captured_responses[0]
            assert cap["agent_name"] == "TestAgent"
            assert cap["response"] == "answer"
            assert cap["is_streaming"] is False
            assert isinstance(cap["timestamp"], datetime)
            assert isinstance(cap["completed_at"], datetime)

        asyncio.run(_run())

    def test_store_responses_false_does_not_accumulate(self):
        async def _run():
            mw = AgentSpeakingCaptureMiddleware(store_responses=False)
            ctx = _make_context()

            async def _next(_ctx):
                pass

            await mw.process(ctx, _next)
            assert mw.get_all_responses() == []

        asyncio.run(_run())

    def test_streaming_captures_placeholder(self):
        async def _run():
            mw = AgentSpeakingCaptureMiddleware()
            ctx = _make_context(is_streaming=True)

            async def _next(_ctx):
                pass

            await mw.process(ctx, _next)

            assert len(mw.captured_responses) == 1
            assert mw.captured_responses[0]["is_streaming"] is True

        asyncio.run(_run())


# ── Callbacks ────────────────────────────────────────────────────────────────


class TestCallbacks:
    def test_sync_callback_invoked(self):
        received = []

        def on_capture(data):
            received.append(data)

        async def _run():
            mw = AgentSpeakingCaptureMiddleware(callback=on_capture)
            ctx = _make_context()

            async def _next(_ctx):
                pass

            await mw.process(ctx, _next)

        asyncio.run(_run())
        assert len(received) == 1
        assert received[0]["agent_name"] == "TestAgent"

    def test_async_callback_invoked(self):
        received = []

        async def on_capture(data):
            received.append(data)

        async def _run():
            mw = AgentSpeakingCaptureMiddleware(callback=on_capture)
            ctx = _make_context()

            async def _next(_ctx):
                pass

            await mw.process(ctx, _next)

        asyncio.run(_run())
        assert len(received) == 1

    def test_stream_complete_callback_only_for_streaming(self):
        stream_calls = []

        async def on_stream(data):
            stream_calls.append(data)

        async def _run():
            mw = AgentSpeakingCaptureMiddleware(on_stream_response_complete=on_stream)

            # Non-streaming — callback should NOT fire
            ctx = _make_context(is_streaming=False)

            async def _next(_ctx):
                pass

            await mw.process(ctx, _next)
            assert len(stream_calls) == 0

            # Streaming — callback SHOULD fire
            ctx2 = _make_context(is_streaming=True)
            await mw.process(ctx2, _next)
            assert len(stream_calls) == 1

        asyncio.run(_run())


# ── Filtering helpers ────────────────────────────────────────────────────────


class TestFilteringHelpers:
    def test_get_responses_by_agent(self):
        async def _run():
            mw = AgentSpeakingCaptureMiddleware()

            async def _next(_ctx):
                pass

            ctx1 = _make_context(agent_name="AgentA", result_text="a1")
            await mw.process(ctx1, _next)
            ctx2 = _make_context(agent_name="AgentB", result_text="b1")
            await mw.process(ctx2, _next)

            assert len(mw.get_responses_by_agent("AgentA")) == 1
            assert len(mw.get_responses_by_agent("AgentB")) == 1
            assert len(mw.get_responses_by_agent("AgentC")) == 0

        asyncio.run(_run())

    def test_clear(self):
        async def _run():
            mw = AgentSpeakingCaptureMiddleware()

            async def _next(_ctx):
                pass

            ctx = _make_context()
            await mw.process(ctx, _next)
            assert len(mw.captured_responses) == 1

            mw.clear()
            assert len(mw.captured_responses) == 0

        asyncio.run(_run())
