# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs.llm_token_telemetry (standardized token usage telemetry)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from libs.llm_token_telemetry import (
    TokenUsage,
    TokenUsageEmitter,
    TokenUsageScope,
    _to_int,
    extract_usage,
    extract_usage_from_dict,
    detect_invoked_tools,
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


# ── TokenUsage dataclass ──────────────────────────────────────────────


class TestTokenUsage:
    """Immutable token-usage record with addition support."""

    def test_defaults_to_zero(self):
        usage = TokenUsage()
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.total_tokens == 0
        assert not usage.has_any

    def test_has_any_true_when_nonzero(self):
        assert TokenUsage(input_tokens=1).has_any
        assert TokenUsage(output_tokens=1).has_any
        assert TokenUsage(total_tokens=1).has_any

    def test_addition(self):
        a = TokenUsage(input_tokens=100, output_tokens=50, total_tokens=150)
        b = TokenUsage(input_tokens=200, output_tokens=80, total_tokens=280)
        result = a + b
        assert result.input_tokens == 300
        assert result.output_tokens == 130
        assert result.total_tokens == 430

    def test_to_event_props(self):
        usage = TokenUsage(input_tokens=10, output_tokens=5, total_tokens=15)
        props = usage.to_event_props()
        assert props == {
            "input_tokens": "10",
            "output_tokens": "5",
            "total_tokens": "15",
        }


# ── extract_usage ──────────────────────────────────────────────────────


class TestExtractUsage:
    """Token extraction from various response shapes."""

    def test_usage_details_dict_with_standard_keys(self):
        response = MagicMock()
        response.usage_details = {
            "input_token_count": 100,
            "output_token_count": 50,
            "total_token_count": 150,
        }
        result = extract_usage(response)
        assert result == TokenUsage(input_tokens=100, output_tokens=50, total_tokens=150)

    def test_usage_details_dict_with_openai_keys(self):
        response = MagicMock()
        response.usage_details = {
            "prompt_tokens": 200,
            "completion_tokens": 80,
            "total_tokens": 280,
        }
        result = extract_usage(response)
        assert result == TokenUsage(input_tokens=200, output_tokens=80, total_tokens=280)

    def test_usage_details_none_falls_to_raw_representation(self):
        response = MagicMock()
        response.usage_details = None
        response.usage = None
        usage_obj = MagicMock()
        usage_obj.prompt_tokens = 300
        usage_obj.completion_tokens = 120
        usage_obj.total_tokens = 420
        usage_obj.input_tokens = 0
        usage_obj.output_tokens = 0
        usage_obj.input_token_count = 0
        usage_obj.output_token_count = 0
        usage_obj.total_token_count = 0
        usage_obj.promptTokens = 0
        usage_obj.completionTokens = 0
        usage_obj.totalTokens = 0
        response.raw_representation.usage = usage_obj
        result = extract_usage(response)
        assert result == TokenUsage(input_tokens=300, output_tokens=120, total_tokens=420)

    def test_raw_representation_dict_usage(self):
        response = MagicMock()
        response.usage_details = None
        response.usage = None
        response.raw_representation.usage = {
            "prompt_tokens": 50,
            "completion_tokens": 25,
            "total_tokens": 75,
        }
        result = extract_usage(response)
        assert result == TokenUsage(input_tokens=50, output_tokens=25, total_tokens=75)

    def test_usage_details_object_with_attributes(self):
        """Handle UsageDetails object (not dict) from agent framework."""
        response = MagicMock()
        usage_obj = MagicMock()
        usage_obj.input_token_count = 400
        usage_obj.output_token_count = 150
        usage_obj.total_token_count = 550
        response.usage_details = usage_obj
        result = extract_usage(response)
        assert result == TokenUsage(input_tokens=400, output_tokens=150, total_tokens=550)

    def test_none_returns_none(self):
        assert extract_usage(None) is None

    def test_no_usage_returns_none(self):
        response = MagicMock()
        response.usage_details = None
        response.usage = None
        response.raw_representation = None
        response.messages = None
        result = extract_usage(response)
        assert result is None

    def test_total_computed_from_input_output_when_missing(self):
        response = MagicMock()
        response.usage_details = {
            "input_token_count": 100,
            "output_token_count": 50,
        }
        result = extract_usage(response)
        assert result.total_tokens == 150


# ── extract_usage_from_dict ───────────────────────────────────────────


class TestExtractUsageFromDict:
    """Extraction from raw dict / SDK usage objects."""

    def test_dict_with_standard_keys(self):
        result = extract_usage_from_dict({
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
        })
        assert result == TokenUsage(input_tokens=100, output_tokens=50, total_tokens=150)

    def test_none_returns_none(self):
        assert extract_usage_from_dict(None) is None


# ── detect_invoked_tools ──────────────────────────────────────────────


class TestDetectInvokedTools:
    """Tool detection from agent result messages."""

    def test_detects_function_calls(self):
        content1 = MagicMock()
        content1.type = "function_call"
        content1.name = "product_agent"
        content2 = MagicMock()
        content2.type = "text"
        content2.name = None
        msg = MagicMock()
        msg.contents = [content1, content2]
        result_obj = MagicMock()
        result_obj.messages = [msg]
        invoked = detect_invoked_tools(result_obj)
        assert invoked == {"product_agent"}

    def test_returns_empty_for_none(self):
        assert detect_invoked_tools(None) == set()


# ── TokenUsageEmitter ─────────────────────────────────────────────────


class TestTokenUsageEmitter:
    """Custom event emission via the standardized emitter."""

    def test_emit_agent_calls_sink(self):
        sink = MagicMock()
        emitter = TokenUsageEmitter(
            connection_string="test",
            event_sink=sink,
            static_dimensions={"app": "content-processing"},
        )
        usage = TokenUsage(input_tokens=100, output_tokens=50, total_tokens=150)
        emitter.emit_agent(
            agent_name="MapHandler",
            model_deployment_name="gpt-4o",
            usage=usage,
            process_id="proc-123",
        )
        sink.assert_called_once()
        call_args = sink.call_args
        assert call_args[0][0] == "LLM_Agent_Token_Usage"
        props = call_args[0][1]
        assert props["agent_name"] == "MapHandler"
        assert props["input_tokens"] == "100"
        assert props["app"] == "content-processing"

    def test_emit_all_emits_agent_model_summary(self):
        sink = MagicMock()
        emitter = TokenUsageEmitter(
            connection_string="test",
            event_sink=sink,
            static_dimensions={"app": "content-processing"},
        )
        usage = TokenUsage(input_tokens=200, output_tokens=80, total_tokens=280)
        emitter.emit_all(
            agent_name="RAI",
            model_deployment_name="gpt-4o",
            usage=usage,
            process_id="proc-456",
        )
        event_names = [call[0][0] for call in sink.call_args_list]
        assert "LLM_Agent_Token_Usage" in event_names
        assert "LLM_Model_Token_Usage" in event_names
        assert "LLM_Token_Usage_Summary" in event_names

    def test_emit_all_agent_count_correct(self):
        sink = MagicMock()
        emitter = TokenUsageEmitter(
            connection_string="test",
            event_sink=sink,
        )
        usage = TokenUsage(input_tokens=100, output_tokens=50, total_tokens=150)
        emitter.emit_all(
            agent_name="MapHandler",
            model_deployment_name="gpt-4o",
            usage=usage,
        )
        # Find the summary event call
        summary_call = next(
            call for call in sink.call_args_list
            if call[0][0] == "LLM_Token_Usage_Summary"
        )
        props = summary_call[0][1]
        assert props["agent_count"] == "1"
        assert props["model_count"] == "1"

    def test_emit_skips_when_not_configured(self):
        emitter = TokenUsageEmitter(connection_string=None, event_sink=None)
        assert not emitter.enabled
        # Should not raise
        emitter.emit("test_event", key="value")

    def test_perf_stats(self):
        sink = MagicMock()
        emitter = TokenUsageEmitter(connection_string="test", event_sink=sink)
        emitter.emit("test_event")
        stats = emitter.perf_stats()
        assert stats["emit_count"] == 1.0
        assert stats["total_ms"] >= 0


# ── TokenUsageScope ──────────────────────────────────────────────────


class TestTokenUsageScope:
    """Context manager that accumulates usage and emits on exit."""

    def test_scope_emits_on_exit(self):
        sink = MagicMock()
        emitter = TokenUsageEmitter(
            connection_string="test",
            event_sink=sink,
            static_dimensions={"app": "content-processing"},
        )
        response = MagicMock()
        response.usage_details = {
            "input_token_count": 100,
            "output_token_count": 50,
            "total_token_count": 150,
        }
        with TokenUsageScope(
            emitter,
            agent_name="MapHandler",
            model_deployment_name="gpt-4o",
            process_id="proc-123",
        ) as scope:
            scope.add(response)

        assert scope.usage.input_tokens == 100
        assert scope.usage.output_tokens == 50
        event_names = [call[0][0] for call in sink.call_args_list]
        assert "LLM_Agent_Token_Usage" in event_names
        assert "LLM_Token_Usage_Summary" in event_names

    def test_scope_handles_no_usage(self):
        sink = MagicMock()
        emitter = TokenUsageEmitter(connection_string="test", event_sink=sink)
        response = MagicMock()
        response.usage_details = None
        response.usage = None
        response.raw_representation = None
        response.messages = None
        with TokenUsageScope(
            emitter,
            agent_name="Test",
            model_deployment_name="gpt-4o",
        ) as scope:
            scope.add(response)

        assert not scope.usage.has_any
        # No events should fire for zero usage
        sink.assert_not_called()

    def test_scope_accumulates_multiple_adds(self):
        sink = MagicMock()
        emitter = TokenUsageEmitter(connection_string="test", event_sink=sink)
        r1 = MagicMock()
        r1.usage_details = {"input_token_count": 100, "output_token_count": 50, "total_token_count": 150}
        r2 = MagicMock()
        r2.usage_details = {"input_token_count": 200, "output_token_count": 80, "total_token_count": 280}
        with TokenUsageScope(
            emitter,
            agent_name="Test",
            model_deployment_name="gpt-4o",
        ) as scope:
            scope.add(r1)
            scope.add(r2)

        assert scope.usage.input_tokens == 300
        assert scope.usage.output_tokens == 130
        assert scope.usage.total_tokens == 430

