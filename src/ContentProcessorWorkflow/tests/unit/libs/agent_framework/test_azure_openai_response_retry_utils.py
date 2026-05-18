# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
from __future__ import annotations

"""Unit tests for Azure OpenAI response retry utilities."""

import pytest
from agent_framework._types import ChatMessage, TextContent

from libs.agent_framework.azure_openai_response_retry import (
    ContextTrimConfig,
    RateLimitRetryConfig,
    _estimate_message_text,
    _get_message_role,
    _looks_like_context_length,
    _looks_like_rate_limit,
    _set_message_text,
    _trim_messages,
    _truncate_text,
)


def test_rate_limit_retry_config_from_env_clamps_invalid_values(monkeypatch) -> None:
    monkeypatch.setenv("AOAI_429_MAX_RETRIES", "-3")
    monkeypatch.setenv("AOAI_429_BASE_DELAY_SECONDS", "-1")
    monkeypatch.setenv("AOAI_429_MAX_DELAY_SECONDS", "not-a-float")

    cfg = RateLimitRetryConfig.from_env()
    assert cfg.max_retries == 0
    assert cfg.base_delay_seconds == 0.0
    # Falls back to default (30.0) on parse failure, then clamped.
    assert cfg.max_delay_seconds == 30.0


def test_looks_like_rate_limit_detects_common_signals() -> None:
    assert _looks_like_rate_limit(Exception("Too Many Requests"))
    assert _looks_like_rate_limit(Exception("rate limit exceeded"))

    class E(Exception):
        pass

    e = E("no message")
    e.status_code = 429
    assert _looks_like_rate_limit(e)


def test_looks_like_context_length_detects_common_signals() -> None:
    assert _looks_like_context_length(Exception("maximum context length"))

    class E(Exception):
        pass

    e = E("something")
    e.status = 413
    assert _looks_like_context_length(e)


def test_truncate_text_includes_marker_and_respects_budget() -> None:
    text = "A" * 200 + "B" * 200
    truncated = _truncate_text(
        text, max_chars=120, keep_head_chars=40, keep_tail_chars=40
    )
    assert len(truncated) <= 120
    assert "TRUNCATED" in truncated


def test_trim_messages_keeps_system_and_tails_and_truncates_long_messages() -> None:
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "X" * 100},
        {"role": "assistant", "content": "Y" * 100},
        {"role": "user", "content": "Z" * 100},
    ]

    cfg = ContextTrimConfig(
        enabled=True,
        max_total_chars=200,
        max_message_chars=50,
        keep_last_messages=2,
        keep_head_chars=20,
        keep_tail_chars=10,
        keep_system_messages=True,
        retry_on_context_error=True,
    )

    trimmed = _trim_messages(messages, cfg=cfg)

    # system message is preserved; tail keeps last 2 non-system messages.
    assert trimmed[0]["role"] == "system"
    assert len(trimmed) == 3

    # Each long message should be truncated to <= max_message_chars.
    assert len(trimmed[1]["content"]) <= 50
    assert len(trimmed[2]["content"]) <= 50


# ---------------------------------------------------------------------------
# ChatMessage-aware helper tests
# ---------------------------------------------------------------------------


class TestGetMessageRole:
    """Verify _get_message_role handles both dict and ChatMessage objects."""

    def test_dict_message(self) -> None:
        assert _get_message_role({"role": "system", "content": "hi"}) == "system"
        assert _get_message_role({"role": "user", "content": "hi"}) == "user"

    def test_chatmessage_system(self) -> None:
        m = ChatMessage(role="system", text="sys prompt")
        assert _get_message_role(m) == "system"

    def test_chatmessage_user(self) -> None:
        m = ChatMessage(role="user", text="user msg")
        assert _get_message_role(m) == "user"

    def test_none_returns_none(self) -> None:
        assert _get_message_role(None) is None


class TestEstimateMessageText:
    """Verify _estimate_message_text extracts text from ChatMessage objects."""

    def test_dict_content(self) -> None:
        assert _estimate_message_text({"content": "hello"}) == "hello"

    def test_chatmessage_text(self) -> None:
        m = ChatMessage(role="user", text="hello world")
        assert _estimate_message_text(m) == "hello world"

    def test_chatmessage_large_text(self) -> None:
        big = "X" * 290_000
        m = ChatMessage(role="user", text=big)
        assert len(_estimate_message_text(m)) == 290_000


class TestSetMessageText:
    """Verify _set_message_text mutates ChatMessage objects correctly."""

    def test_dict_message(self) -> None:
        m = {"role": "user", "content": "old"}
        result = _set_message_text(m, "new")
        assert result["content"] == "new"

    def test_chatmessage_replaces_contents(self) -> None:
        m = ChatMessage(role="user", text="A" * 100_000)
        result = _set_message_text(m, "truncated")
        assert result.text == "truncated"
        assert len(result.contents) == 1
        assert isinstance(result.contents[0], TextContent)


class TestTrimMessagesWithChatMessage:
    """Integration tests for _trim_messages with ChatMessage objects.

    These reproduce the exact bug scenario from production: 2 ChatMessage
    objects totalling ~290K chars were trimmed to 0 messages.
    """

    @pytest.fixture()
    def tight_cfg(self) -> ContextTrimConfig:
        """Config with a budget smaller than the test messages to force trimming."""
        return ContextTrimConfig(
            enabled=True,
            max_total_chars=50_000,
            max_message_chars=30_000,
            keep_last_messages=40,
            keep_head_chars=5_000,
            keep_tail_chars=2_000,
            keep_system_messages=True,
            retry_on_context_error=True,
        )

    def test_never_returns_empty_list(self, tight_cfg: ContextTrimConfig) -> None:
        """Core regression: _trim_messages must never return an empty list."""
        messages = [
            ChatMessage(role="system", text="S" * 5_000),
            ChatMessage(role="user", text="U" * 285_000),
        ]
        result = _trim_messages(messages, cfg=tight_cfg)
        assert len(result) >= 1, "trim must never drop all messages"

    def test_system_message_preserved(self, tight_cfg: ContextTrimConfig) -> None:
        """System message must be kept even when non-system messages are dropped."""
        messages = [
            ChatMessage(role="system", text="System instructions"),
            ChatMessage(role="user", text="U" * 285_000),
        ]
        result = _trim_messages(messages, cfg=tight_cfg)
        assert _get_message_role(result[0]) == "system"

    def test_truncation_respects_budget(self, tight_cfg: ContextTrimConfig) -> None:
        """After trimming, total chars must not exceed max_total_chars."""
        messages = [
            ChatMessage(role="system", text="S" * 5_000),
            ChatMessage(role="user", text="U" * 285_000),
        ]
        result = _trim_messages(messages, cfg=tight_cfg)
        total = sum(len(_estimate_message_text(m)) for m in result)
        assert total <= tight_cfg.max_total_chars

    def test_single_huge_message(self, tight_cfg: ContextTrimConfig) -> None:
        """A single message exceeding the budget is truncated, not dropped."""
        messages = [ChatMessage(role="user", text="X" * 500_000)]
        result = _trim_messages(messages, cfg=tight_cfg)
        assert len(result) == 1
        assert len(_estimate_message_text(result[0])) <= tight_cfg.max_total_chars

    def test_production_scenario_290k(self) -> None:
        """Reproduce the exact production failure: 290K chars → must not become 0."""
        cfg = ContextTrimConfig(
            enabled=True,
            max_total_chars=240_000,  # Old default that caused the bug
            max_message_chars=20_000,
            keep_last_messages=40,
            keep_head_chars=10_000,
            keep_tail_chars=3_000,
            keep_system_messages=True,
            retry_on_context_error=True,
        )
        messages = [
            ChatMessage(role="system", text="S" * 5_607),
            ChatMessage(role="user", text="U" * 285_000),
        ]
        result = _trim_messages(messages, cfg=cfg)
        assert len(result) >= 1, "must keep at least 1 message"
        total = sum(len(_estimate_message_text(m)) for m in result)
        assert total <= cfg.max_total_chars

    def test_default_config_allows_290k(self) -> None:
        """With new defaults (800K budget), 290K input passes without trimming."""
        cfg = ContextTrimConfig.from_env()
        messages = [
            ChatMessage(role="system", text="S" * 5_607),
            ChatMessage(role="user", text="U" * 285_000),
        ]
        result = _trim_messages(messages, cfg=cfg)
        # 290K < 800K, so no trimming should occur; all messages kept intact.
        assert len(result) == 2
        assert _estimate_message_text(result[0]) == "S" * 5_607
        assert _estimate_message_text(result[1]) == "U" * 285_000
