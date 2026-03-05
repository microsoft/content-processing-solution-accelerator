# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for utils/prompt_util.py (Jinja2 template rendering)."""

from __future__ import annotations

import pytest

from utils.prompt_util import TemplateUtility


class TestRender:
    def test_simple_substitution(self):
        result = TemplateUtility.render("Hello {{ name }}!", name="World")
        assert result == "Hello World!"

    def test_no_variables(self):
        result = TemplateUtility.render("Plain text")
        assert result == "Plain text"

    def test_multiple_variables(self):
        result = TemplateUtility.render(
            "{{ a }} + {{ b }} = {{ c }}", a="1", b="2", c="3"
        )
        assert result == "1 + 2 = 3"

    def test_unused_kwargs_ignored(self):
        result = TemplateUtility.render("{{ x }}", x="used", y="ignored")
        assert result == "used"


class TestRenderFromFile:
    def test_renders_template_file(self, tmp_path):
        template_file = tmp_path / "prompt.txt"
        template_file.write_text("Hi {{ user }}!", encoding="utf-8")

        result = TemplateUtility.render_from_file(str(template_file), user="Alice")
        assert result == "Hi Alice!"

    def test_multiline_template(self, tmp_path):
        template_file = tmp_path / "multi.txt"
        template_file.write_text(
            "Line1: {{ a }}\nLine2: {{ b }}", encoding="utf-8"
        )

        result = TemplateUtility.render_from_file(
            str(template_file), a="X", b="Y"
        )
        assert result == "Line1: X\nLine2: Y"

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            TemplateUtility.render_from_file("/nonexistent/path.txt")
