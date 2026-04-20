# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs.application.application_configuration (settings and validators)."""

from __future__ import annotations

from libs.application.application_configuration import AppConfiguration

# ── TestAppConfiguration ────────────────────────────────────────────────


class TestAppConfiguration:
    """Field validator for process step splitting."""

    def test_split_processes_from_csv(self):
        result = AppConfiguration.split_processes("extract,transform,save")
        assert result == ["extract", "transform", "save"]

    def test_split_processes_single(self):
        result = AppConfiguration.split_processes("extract")
        assert result == ["extract"]

    def test_split_processes_passthrough_list(self):
        result = AppConfiguration.split_processes(["a", "b"])
        assert result == ["a", "b"]
