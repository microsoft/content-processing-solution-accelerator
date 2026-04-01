# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
from __future__ import annotations

"""Unit tests for InputObserverMiddleware."""

import asyncio
from types import SimpleNamespace

from agent_framework import ChatMessage, Role

from libs.agent_framework.middlewares import InputObserverMiddleware


def test_input_observer_middleware_replaces_user_text_when_configured() -> None:
    async def _run() -> None:
        ctx = SimpleNamespace(
            messages=[
                ChatMessage(role=Role.USER, text="original"),
            ]
        )

        mw = InputObserverMiddleware(replacement="replacement")

        async def _next(_context):
            return None

        await mw.process(ctx, _next)

        assert ctx.messages[0].role == Role.USER
        assert ctx.messages[0].text == "replacement"

    asyncio.run(_run())
