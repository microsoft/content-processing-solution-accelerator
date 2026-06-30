# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs.pipeline.queue_handler_base (HandlerBase ABC)."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest
from azure.storage.queue import QueueClient

from libs.application.application_context import AppContext
from libs.pipeline.entities.pipeline_message_context import MessageContext
from libs.pipeline.entities.pipeline_step_result import StepResult
from libs.pipeline.queue_handler_base import HandlerBase


class _MockHandler(HandlerBase):
    async def execute(self, context: MessageContext) -> StepResult:
        return StepResult(
            process_id="1234",
            step_name="extract",
            result={"result": "success", "data": {"key": "value"}},
        )


@pytest.fixture
def mock_queue_helper(mocker):
    mocker.patch(
        "libs.pipeline.pipeline_queue_helper.create_queue_client_name",
        return_value="test-queue",
    )
    mocker.patch(
        "libs.pipeline.pipeline_queue_helper.create_dead_letter_queue_client_name",
        return_value="test-dlq",
    )
    mocker.patch(
        "libs.pipeline.pipeline_queue_helper.create_or_get_queue_client",
        return_value=MagicMock(spec=QueueClient),
    )
    return mocker


@pytest.fixture
def mock_app_context():
    ctx = MagicMock(spec=AppContext)
    cfg = MagicMock()
    cfg.app_storage_queue_url = "https://testqueueurl.com"
    cfg.app_storage_blob_url = "https://testbloburl.com"
    cfg.app_cps_processes = "TestProcess"
    ctx.configuration = cfg
    ctx.credential = MagicMock()
    return ctx


# ── TestHandlerBase ─────────────────────────────────────────────────────


class TestHandlerBase:
    """HandlerBase execute dispatch and queue introspection."""

    def test_execute_returns_step_result(self):
        handler = _MockHandler(appContext=MagicMock(), step_name="extract")
        message_context = MagicMock(spec=MessageContext)

        async def _run():
            return await handler.execute(message_context)

        result = asyncio.run(_run())
        assert result.step_name == "extract"
        assert result.result == {"result": "success", "data": {"key": "value"}}

    def test_show_queue_information(self, mock_queue_helper, mock_app_context):
        handler = _MockHandler(appContext=mock_app_context, step_name="extract")
        mock_queue_client = MagicMock(spec=QueueClient)
        mock_queue_client.url = "https://testurl"
        mock_queue_client.get_queue_properties.return_value = MagicMock(
            approximate_message_count=5
        )
        handler.queue_client = mock_queue_client
        handler._show_queue_information()
