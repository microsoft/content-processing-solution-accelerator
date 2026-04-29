# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for the RAI executor and RAI response model.

Covers prompt loading (``_load_rai_executor_prompt``), the
``RAIResponse`` Pydantic model, and the ``fetch_processed_steps_result``
URL-building logic.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from steps.rai.model.rai_response import RAIResponse

# The @handler decorator in agent_framework validates type annotations at
# import time, which fails in the test environment.  Patch it to a no-op
# before importing the executor module.
with patch("agent_framework.handler", lambda fn: fn):
    from steps.rai.executor.rai_executor import RAIExecutor


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_executor() -> RAIExecutor:
    """Create a RAIExecutor without a real AppContext."""
    with patch.object(RAIExecutor, "__init__", lambda self, *a, **kw: None):
        exe = RAIExecutor.__new__(RAIExecutor)
    exe._PROMPT_FILE_NAME = "rai_executor_prompt.txt"
    return exe


# ── RAIResponse model ───────────────────────────────────────────────────────


class TestRAIResponse:
    """Tests for the RAIResponse Pydantic model."""

    def test_safe_response(self):
        resp = RAIResponse(IsNotSafe=False, Reasoning="Content is clean.")
        assert resp.IsNotSafe is False
        assert resp.Reasoning == "Content is clean."

    def test_unsafe_response(self):
        resp = RAIResponse(IsNotSafe=True, Reasoning="Violent language detected.")
        assert resp.IsNotSafe is True
        assert "Violent" in resp.Reasoning

    def test_missing_required_field_raises(self):
        with pytest.raises(Exception):
            RAIResponse(IsNotSafe=True)  # type: ignore[call-arg]

    def test_missing_is_not_safe_raises(self):
        with pytest.raises(Exception):
            RAIResponse(Reasoning="oops")  # type: ignore[call-arg]

    def test_round_trip_serialization(self):
        original = RAIResponse(IsNotSafe=False, Reasoning="OK")
        data = original.model_dump()
        restored = RAIResponse.model_validate(data)
        assert restored == original

    def test_json_round_trip(self):
        original = RAIResponse(IsNotSafe=True, Reasoning="Blocked")
        json_str = original.model_dump_json()
        restored = RAIResponse.model_validate_json(json_str)
        assert restored == original

    def test_field_types(self):
        resp = RAIResponse(IsNotSafe=False, Reasoning="Fine")
        assert isinstance(resp.IsNotSafe, bool)
        assert isinstance(resp.Reasoning, str)


# ── Prompt loading ───────────────────────────────────────────────────────────


class TestLoadRAIExecutorPrompt:
    """Tests for RAIExecutor._load_rai_executor_prompt."""

    def test_loads_real_prompt_file(self):
        """The actual prompt file should exist and be non-empty."""
        exe = _make_executor()
        prompt = exe._load_rai_executor_prompt()
        assert len(prompt) > 0
        assert isinstance(prompt, str)

    def test_prompt_contains_expected_keywords(self):
        """Sanity-check that the prompt mentions core safety keywords."""
        exe = _make_executor()
        prompt = exe._load_rai_executor_prompt()
        assert "TRUE" in prompt
        assert "FALSE" in prompt
        assert "safety" in prompt.lower()
        assert "IsNotSafe" in prompt
        assert "Reasoning" in prompt
        assert "document-processing pipeline" in prompt

    def test_raises_on_missing_file(self):
        """A nonexistent prompt filename triggers RuntimeError."""
        exe = _make_executor()
        exe._PROMPT_FILE_NAME = "this_file_does_not_exist_anywhere.txt"
        with pytest.raises(RuntimeError, match="Missing RAI executor prompt"):
            exe._load_rai_executor_prompt()

    def test_raises_on_empty_file(self):
        """An all-whitespace prompt file triggers RuntimeError."""
        exe = _make_executor()
        with patch.object(Path, "read_text", return_value="   \n  "):
            with pytest.raises(RuntimeError, match="empty"):
                exe._load_rai_executor_prompt()

    def test_prompt_is_stripped(self):
        """Leading/trailing whitespace is removed from the loaded prompt."""
        exe = _make_executor()
        with patch.object(Path, "read_text", return_value="  Hello prompt  \n"):
            prompt = exe._load_rai_executor_prompt()
            assert prompt == "Hello prompt"


# ── fetch_processed_steps_result URL logic ──────────────────────────────────


class TestFetchProcessedStepsResult:
    """Tests for RAIExecutor.fetch_processed_steps_result."""

    def _make_executor_with_endpoint(self, endpoint: str) -> RAIExecutor:
        """Create a RAIExecutor with a mock app_context returning *endpoint*."""
        exe = _make_executor()
        config = MagicMock()
        config.app_cps_content_process_endpoint = endpoint
        context = MagicMock()
        context.configuration = config
        exe.app_context = context
        return exe

    def test_url_with_contentprocessor_suffix(self):
        """When endpoint ends with /contentprocessor, use /submit path."""
        exe = self._make_executor_with_endpoint("https://example.com/contentprocessor")
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json.return_value = [{"step_name": "extract"}]

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "steps.rai.executor.rai_executor.HttpRequestClient",
            return_value=mock_client,
        ):
            result = asyncio.run(exe.fetch_processed_steps_result("proc-123"))

        mock_client.get.assert_called_once_with(
            "https://example.com/contentprocessor/submit/proc-123/steps"
        )
        assert result == [{"step_name": "extract"}]

    def test_url_without_contentprocessor_suffix(self):
        """When endpoint does not end with /contentprocessor, use /contentprocessor/processed."""
        exe = self._make_executor_with_endpoint("https://example.com/api")
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json.return_value = [{"step_name": "map"}]

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "steps.rai.executor.rai_executor.HttpRequestClient",
            return_value=mock_client,
        ):
            result = asyncio.run(exe.fetch_processed_steps_result("proc-456"))

        mock_client.get.assert_called_once_with(
            "https://example.com/api/contentprocessor/processed/proc-456/steps"
        )
        assert result == [{"step_name": "map"}]

    def test_returns_none_on_non_200(self):
        """Non-200 responses yield None."""
        exe = self._make_executor_with_endpoint("https://example.com/api")
        mock_response = MagicMock()
        mock_response.status = 404

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "steps.rai.executor.rai_executor.HttpRequestClient",
            return_value=mock_client,
        ):
            result = asyncio.run(exe.fetch_processed_steps_result("proc-789"))

        assert result is None

    def test_trailing_slash_stripped_from_endpoint(self):
        """Trailing slashes on the endpoint are stripped before URL assembly."""
        exe = self._make_executor_with_endpoint("https://example.com/api/")
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json.return_value = []

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "steps.rai.executor.rai_executor.HttpRequestClient",
            return_value=mock_client,
        ):
            asyncio.run(exe.fetch_processed_steps_result("proc-000"))

        url_called = mock_client.get.call_args[0][0]
        assert "/api/contentprocessor/processed/proc-000/steps" in url_called
        assert "//" not in url_called.split("://")[1]

    def test_none_endpoint_handled(self):
        """None endpoint defaults to empty string without crashing."""
        exe = self._make_executor_with_endpoint(None)  # type: ignore[arg-type]
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json.return_value = []

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "steps.rai.executor.rai_executor.HttpRequestClient",
            return_value=mock_client,
        ):
            result = asyncio.run(exe.fetch_processed_steps_result("proc-nil"))

        assert result == []
