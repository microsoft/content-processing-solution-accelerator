# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for the RAI executor and RAI response model.

Covers prompt loading (``_load_rai_executor_prompt``), the
``RAIResponse`` Pydantic model, and the ``fetch_processed_steps_result``
direct-resource-access logic.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from steps.rai.model.rai_response import RAIResponse

# The @handler decorator in agent_framework validates type annotations at
# import time, which fails in the test environment.  Patch it to a no-op
# before importing the executor module.
_orig_handler = sys.modules.get("agent_framework", MagicMock()).handler  # type: ignore[union-attr]

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
        resp = RAIResponse(IsNotSafe=False)
        assert resp.IsNotSafe is False

    def test_unsafe_response(self):
        resp = RAIResponse(IsNotSafe=True)
        assert resp.IsNotSafe is True

    def test_missing_is_not_safe_raises(self):
        with pytest.raises(Exception):
            RAIResponse()  # type: ignore[call-arg]

    def test_round_trip_serialization(self):
        original = RAIResponse(IsNotSafe=False)
        data = original.model_dump()
        restored = RAIResponse.model_validate(data)
        assert restored == original

    def test_json_round_trip(self):
        original = RAIResponse(IsNotSafe=True)
        json_str = original.model_dump_json()
        restored = RAIResponse.model_validate_json(json_str)
        assert restored == original

    def test_field_types(self):
        resp = RAIResponse(IsNotSafe=False)
        assert isinstance(resp.IsNotSafe, bool)


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
    """Tests for RAIExecutor.fetch_processed_steps_result.

    The method now delegates to ContentProcessService.get_steps()
    via app_context instead of using HttpRequestClient.
    """

    def _make_executor_with_mock_service(self, return_value=None):
        """Create a RAIExecutor with a mocked ContentProcessService."""
        exe = _make_executor()
        mock_service = MagicMock()
        mock_service.get_steps.return_value = return_value
        context = MagicMock()
        context.get_service.return_value = mock_service
        exe.app_context = context
        return exe, mock_service

    def test_returns_steps_list(self):
        """get_steps returns a list of step dicts."""
        steps = [{"step_name": "extract"}, {"step_name": "map"}]
        exe, mock_svc = self._make_executor_with_mock_service(steps)
        result = asyncio.run(exe.fetch_processed_steps_result("proc-123"))
        mock_svc.get_steps.assert_called_once_with("proc-123")
        assert result == steps

    def test_returns_none_when_not_found(self):
        """get_steps returns None when blob not found."""
        exe, mock_svc = self._make_executor_with_mock_service(None)
        result = asyncio.run(exe.fetch_processed_steps_result("proc-789"))
        assert result is None

    def test_returns_empty_list(self):
        """get_steps can return an empty list."""
        exe, mock_svc = self._make_executor_with_mock_service([])
        result = asyncio.run(exe.fetch_processed_steps_result("proc-000"))
        assert result == []
