# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for GapExecutor prompt/rules loading."""

from __future__ import annotations

from unittest.mock import patch

import pytest

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
