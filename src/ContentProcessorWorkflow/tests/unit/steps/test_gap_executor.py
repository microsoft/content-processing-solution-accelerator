# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for GapExecutor prompt/rules loading."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

with patch.dict(
    sys.modules,
    {
        "repositories.claim_processes": MagicMock(Claim_Processes=object),
        "services.content_process_service": MagicMock(ContentProcessService=object),
    },
):
    with patch("agent_framework.handler", lambda fn: fn):
        from steps.gap_analysis.executor.gap_executor import GapExecutor


class TestReadTextFile:
    def _make_executor(self):
        """Create a GapExecutor without a real app context."""
        with patch.object(GapExecutor, "__init__", lambda self, *a, **kw: None):
            exe = GapExecutor.__new__(GapExecutor)
        exe._PROMPT_FILE_NAME = "gap_executor_prompt.txt"
        exe._RULES_FILE_NAME = "fnol_gap_rules.dsl.yaml"
        return exe

    def test_reads_text_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world", encoding="utf-8")
        exe = self._make_executor()
        assert exe._read_text_file(f) == "hello world"

    def test_raises_on_empty_file(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("   \n  ", encoding="utf-8")
        exe = self._make_executor()
        with pytest.raises(RuntimeError, match="empty"):
            exe._read_text_file(f)


class TestLoadPromptAndRules:
    def _make_executor(self):
        with patch.object(GapExecutor, "__init__", lambda self, *a, **kw: None):
            exe = GapExecutor.__new__(GapExecutor)
        exe._PROMPT_FILE_NAME = "gap_executor_prompt.txt"
        exe._RULES_FILE_NAME = "fnol_gap_rules.dsl.yaml"
        return exe

    def test_loads_real_prompt_and_rules(self):
        """The actual prompt and rules files should exist and load correctly."""
        exe = self._make_executor()
        prompt = exe._load_prompt_and_rules()
        assert len(prompt) > 0
        assert isinstance(prompt, str)
        # The rules should have been injected (no placeholder remaining)
        assert "{{RULES_DSL}}" not in prompt

    def test_raises_on_invalid_yaml_rules(self):
        """If the YAML rules file is invalid, should raise RuntimeError."""
        exe = self._make_executor()

        call_count = [0]

        def fake_read(path):
            call_count[0] += 1
            if call_count[0] == 1:
                return "Prompt: {{RULES_DSL}}"
            else:
                return "invalid: yaml: [broken"

        exe._read_text_file = fake_read

        with pytest.raises(RuntimeError, match="Invalid YAML"):
            exe._load_prompt_and_rules()


class TestSerializeProcessedOutput:
    def _make_executor(self):
        with patch.object(GapExecutor, "__init__", lambda self, *a, **kw: None):
            exe = GapExecutor.__new__(GapExecutor)
        exe._PROMPT_FILE_NAME = "gap_executor_prompt.txt"
        exe._RULES_FILE_NAME = "fnol_gap_rules.dsl.yaml"
        return exe

    def test_serializes_datetime_values(self):
        exe = self._make_executor()

        serialized = exe._serialize_processed_output(
            {
                "created_at": datetime(2026, 3, 27, 12, 56, 20),
                "nested": {"updated_at": datetime(2026, 3, 27, 13, 1, 2)},
            }
        )

        assert json.loads(serialized) == {
            "created_at": "2026-03-27T12:56:20",
            "nested": {"updated_at": "2026-03-27T13:01:02"},
        }
