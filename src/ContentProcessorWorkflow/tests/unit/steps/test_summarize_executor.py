# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for SummarizeExecutor prompt loading."""

from __future__ import annotations

import pytest
from unittest.mock import patch
from pathlib import Path

from steps.summarize.executor.summarize_executor import SummarizeExecutor


class TestLoadClaimSummarizationPrompt:
    def _make_executor(self):
        """Create a SummarizeExecutor without a real app context."""
        with patch.object(SummarizeExecutor, "__init__", lambda self, *a, **kw: None):
            exe = SummarizeExecutor.__new__(SummarizeExecutor)
        exe._PROMPT_FILE_NAME = "summarize_executor_prompt.txt"
        return exe

    def test_loads_real_prompt_file(self):
        """The actual prompt file should exist and be non-empty."""
        exe = self._make_executor()
        prompt = exe._load_claim_summarization_prompt()
        assert len(prompt) > 0
        assert isinstance(prompt, str)

    def test_raises_on_missing_file(self):
        """A nonexistent prompt filename triggers RuntimeError."""
        exe = self._make_executor()
        exe._PROMPT_FILE_NAME = "this_file_does_not_exist_anywhere.txt"
        with pytest.raises(RuntimeError, match="Missing summarization prompt"):
            exe._load_claim_summarization_prompt()

    def test_raises_on_empty_file(self):
        """An all-whitespace prompt file triggers RuntimeError."""
        exe = self._make_executor()
        with patch.object(Path, "read_text", return_value="   \n  "):
            with pytest.raises(RuntimeError, match="empty"):
                exe._load_claim_summarization_prompt()
