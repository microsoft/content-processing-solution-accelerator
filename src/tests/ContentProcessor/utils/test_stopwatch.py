# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs.utils.stopwatch (elapsed-time measurement)."""

from __future__ import annotations

from libs.utils.stopwatch import Stopwatch

# ── TestStopwatch ───────────────────────────────────────────────────────


class TestStopwatch:
    """Start / stop / reset / context-manager lifecycle."""

    def test_initial_state(self):
        sw = Stopwatch()
        assert sw.elapsed == 0
        assert sw.elapsed_string == "0:00:00"
        assert not sw.is_running

    def test_start(self, mocker):
        mocker.patch("time.perf_counter", return_value=100.0)
        sw = Stopwatch()
        sw.start()
        assert sw.is_running
        assert sw.start_time == 100.0

    def test_stop(self, mocker):
        mocker.patch("time.perf_counter", side_effect=[100.0, 105.0])
        sw = Stopwatch()
        sw.start()
        sw.stop()
        assert not sw.is_running
        assert sw.elapsed == 5.0
        assert sw.elapsed_string == "00:00:05.000"

    def test_reset(self):
        sw = Stopwatch()
        sw.start()
        sw.stop()
        sw.reset()
        assert sw.elapsed == 0
        assert not sw.is_running

    def test_context_manager(self, mocker):
        mocker.patch("time.perf_counter", side_effect=[100.0, 105.0])
        with Stopwatch() as sw:
            assert sw.is_running
        assert not sw.is_running
        assert sw.elapsed == 5.0
        assert sw.elapsed_string == "00:00:05.000"

    def test_format_elapsed_time(self):
        sw = Stopwatch()
        assert sw._format_elapsed_time(3661.123) == "01:01:01.123"
