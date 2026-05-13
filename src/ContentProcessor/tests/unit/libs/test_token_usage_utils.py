# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs.token_usage_utils (token usage extraction and event emission)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from libs.token_usage_utils import (
    _to_int,
    emit_agent_token_event,
    emit_model_token_event,
    emit_summary_token_event,
    extract_token_usage,
)


# ── _to_int helper ─────────────────────────────────────────────────────


class TestToInt:
    """Conversion helper for safely casting token counts."""

    def test_none_returns_default(self):
        assert _to_int(None) == 0

    def test_bool_returns_default(self):
        assert _to_int(True) == 0
        assert _to_int(False) == 0

    def test_int_passthrough(self):
        assert _to_int(42) == 42

    def test_float_truncates(self):
        assert _to_int(3.7) == 3

    def test_digit_string(self):
        assert _to_int("100") == 100

    def test_non_digit_string_returns_default(self):
        assert _to_int("abc") == 0

    def test_custom_default(self):
        assert _to_int(None, default=5) == 5


# ── extract_token_usage ────────────────────────────────────────────────


class TestExtractTokenUsage:
    """Token extraction from various response shapes."""

    def test_usage_details_dict_with_standard_keys(self):
        response = MagicMock()
        response.usage_details = {
            "input_token_count": 100,
            "output_token_count": 50,
            "total_token_count": 150,
        }
        result = extract_token_usage(response)
        assert result == {
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
        }

    def test_usage_details_dict_with_openai_keys(self):
        response = MagicMock()
        response.usage_details = {
            "prompt_tokens": 200,
            "completion_tokens": 80,
            "total_tokens": 280,
        }
        result = extract_token_usage(response)
        assert result == {
            "input_tokens": 200,
            "output_tokens": 80,
            "total_tokens": 280,
        }

    def test_usage_details_none_falls_to_raw_representation(self):
        response = MagicMock()
        response.usage_details = None
        usage_obj = MagicMock()
        usage_obj.prompt_tokens = 300
        usage_obj.completion_tokens = 120
        usage_obj.total_tokens = 420
        usage_obj.input_tokens = 0
        usage_obj.output_tokens = 0
        response.raw_representation.usage = usage_obj
        result = extract_token_usage(response)
        assert result == {
            "input_tokens": 300,
            "output_tokens": 120,
            "total_tokens": 420,
        }

    def test_raw_representation_dict_usage(self):
        response = MagicMock()
        response.usage_details = None
        response.raw_representation.usage = {
            "prompt_tokens": 50,
            "completion_tokens": 25,
            "total_tokens": 75,
        }
        result = extract_token_usage(response)
        assert result == {
            "input_tokens": 50,
            "output_tokens": 25,
            "total_tokens": 75,
        }

    def test_usage_details_object_with_attributes(self):
        """Handle UsageDetails object (not dict) from agent framework."""
        response = MagicMock()
        usage_obj = MagicMock()
        usage_obj.input_token_count = 400
        usage_obj.output_token_count = 150
        usage_obj.total_token_count = 550
        response.usage_details = usage_obj
        result = extract_token_usage(response)
        assert result == {
            "input_tokens": 400,
            "output_tokens": 150,
            "total_tokens": 550,
        }

    def test_no_usage_returns_zeros(self):
        response = MagicMock()
        response.usage_details = None
        response.raw_representation = None
        result = extract_token_usage(response)
        assert result == {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }

    def test_total_computed_from_input_output_when_missing(self):
        response = MagicMock()
        response.usage_details = {
            "input_token_count": 100,
            "output_token_count": 50,
        }
        result = extract_token_usage(response)
        assert result["total_tokens"] == 150


# ── emit_agent_token_event ─────────────────────────────────────────────


class TestEmitAgentTokenEvent:
    """Custom event emission for per-agent token usage."""

    @patch("libs.token_usage_utils._track_event_if_configured")
    def test_emits_correct_event(self, mock_track):
        usage = {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}
        emit_agent_token_event(
            agent_name="MapHandler",
            model_deployment_name="gpt-4o",
            usage=usage,
            process_id="proc-123",
        )
        mock_track.assert_called_once_with("LLM_Agent_Token_Usage", {
            "agent_name": "MapHandler",
            "input_tokens": "100",
            "output_tokens": "50",
            "total_tokens": "150",
            "model_deployment_name": "gpt-4o",
            "process_id": "proc-123",
        })


# ── emit_model_token_event ─────────────────────────────────────────────


class TestEmitModelTokenEvent:
    """Custom event emission for per-model token usage."""

    @patch("libs.token_usage_utils._track_event_if_configured")
    def test_emits_correct_event(self, mock_track):
        usage = {"input_tokens": 200, "output_tokens": 80, "total_tokens": 280}
        emit_model_token_event(
            model_deployment_name="gpt-4o",
            usage=usage,
            process_id="proc-456",
        )
        mock_track.assert_called_once_with("LLM_Model_Token_Usage", {
            "model_deployment_name": "gpt-4o",
            "input_tokens": "200",
            "output_tokens": "80",
            "total_tokens": "280",
            "process_id": "proc-456",
        })


# ── emit_summary_token_event ──────────────────────────────────────────


class TestEmitSummaryTokenEvent:
    """Custom event emission for document-level token summary."""

    @patch("libs.token_usage_utils._track_event_if_configured")
    def test_emits_correct_event(self, mock_track):
        emit_summary_token_event(
            total_input_tokens=500,
            total_output_tokens=200,
            total_tokens=700,
            process_id="proc-789",
            file_name="test.pdf",
            file_mime_type="application/pdf",
            agent_count=2,
            model_count=1,
        )
        mock_track.assert_called_once_with("LLM_Token_Usage_Summary", {
            "total_input_tokens": "500",
            "total_output_tokens": "200",
            "total_tokens": "700",
            "process_id": "proc-789",
            "file_name": "test.pdf",
            "file_mime_type": "application/pdf",
            "agent_count": "2",
            "model_count": "1",
        })


# ── _track_event_if_configured ────────────────────────────────────────


class TestTrackEventIfConfigured:
    """Application Insights event tracking guard."""

    @patch.dict("os.environ", {"APPLICATIONINSIGHTS_CONNECTION_STRING": "InstrumentationKey=test"})
    @patch("azure.monitor.events.extension.track_event")
    def test_tracks_when_configured(self, mock_track_event):
        from libs.token_usage_utils import _track_event_if_configured

        _track_event_if_configured("test_event", {"key": "value"})
        mock_track_event.assert_called_once_with("test_event", {"key": "value"})

    @patch.dict("os.environ", {}, clear=True)
    def test_skips_when_not_configured(self):
        from libs.token_usage_utils import _track_event_if_configured

        _track_event_if_configured("test_event", {"key": "value"})
