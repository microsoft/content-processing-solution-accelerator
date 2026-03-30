# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs.agent_framework.azure_openai_response_retry (transient error detection)."""

from __future__ import annotations

import sys
from types import ModuleType

import pytest

# ---------------------------------------------------------------------------
# Stub the external ``agent_framework`` package so the module under test can
# be imported in environments where the package is not installed.
# ---------------------------------------------------------------------------
_af = ModuleType("agent_framework")
_af_azure = ModuleType("agent_framework.azure")

_af_azure.AzureOpenAIChatClient = type("AzureOpenAIChatClient", (), {})  # type: ignore[attr-defined]
_af_azure.AzureOpenAIResponsesClient = type("AzureOpenAIResponsesClient", (), {})  # type: ignore[attr-defined]

sys.modules.setdefault("agent_framework", _af)
sys.modules.setdefault("agent_framework.azure", _af_azure)

from libs.agent_framework.azure_openai_response_retry import (  # noqa: E402
    RateLimitRetryConfig,
    _is_transient_error,
    _looks_like_access_check_challenge,
    _looks_like_rate_limit,
)

# ── _looks_like_rate_limit ──────────────────────────────────────────────────


class TestLooksLikeRateLimit:
    """Detects 429 / rate-limit errors from various error shapes."""

    @pytest.mark.parametrize(
        "msg",
        [
            "Too many requests",
            "rate limit exceeded",
            "HTTP 429",
            "throttle limit reached",
        ],
    )
    def test_matches_rate_limit_messages(self, msg: str):
        assert _looks_like_rate_limit(RuntimeError(msg)) is True

    def test_matches_status_code_429(self):
        exc = RuntimeError("something")
        exc.status_code = 429  # type: ignore[attr-defined]
        assert _looks_like_rate_limit(exc) is True

    def test_matches_status_attribute_429(self):
        exc = RuntimeError("something")
        exc.status = 429  # type: ignore[attr-defined]
        assert _looks_like_rate_limit(exc) is True

    def test_non_rate_limit_returns_false(self):
        assert _looks_like_rate_limit(RuntimeError("bad request")) is False

    def test_follows_cause_chain(self):
        inner = RuntimeError("rate limit exceeded")
        outer = RuntimeError("wrapper")
        outer.__cause__ = inner
        assert _looks_like_rate_limit(outer) is True


# ── _looks_like_access_check_challenge ──────────────────────────────────────


class TestLooksLikeAccessCheckChallenge:
    """Detects Azure AI Services gateway challenge-response errors."""

    def test_matches_check_access_header_message(self):
        msg = (
            "Error code: 400 - {'error': {'message': "
            "\"Required header 'check-access-response-enc' is missing or empty.\"}}"
        )
        assert _looks_like_access_check_challenge(RuntimeError(msg)) is True

    def test_matches_account_information_error(self):
        msg = (
            "Error code: 404 - {'error': {'message': "
            "'Could not obtain the account information.', "
            "'type': 'invalid_request_error', 'param': None, 'code': None}}"
        )
        assert _looks_like_access_check_challenge(RuntimeError(msg)) is True

    def test_matches_case_insensitive(self):
        msg = "header Check-Access-Response-Enc is required"
        assert _looks_like_access_check_challenge(RuntimeError(msg)) is True

    def test_non_matching_returns_false(self):
        assert _looks_like_access_check_challenge(RuntimeError("bad request")) is False

    def test_follows_cause_chain(self):
        inner = RuntimeError("check-access-response-enc missing")
        outer = RuntimeError("wrapper")
        outer.__cause__ = inner
        assert _looks_like_access_check_challenge(outer) is True

    def test_does_not_infinite_loop_on_self_cause(self):
        exc = RuntimeError("something")
        exc.__cause__ = exc
        assert _looks_like_access_check_challenge(exc) is False


# ── _is_transient_error ─────────────────────────────────────────────────────


class TestIsTransientError:
    """Combined predicate for retryable transient errors."""

    def test_rate_limit_is_transient(self):
        assert _is_transient_error(RuntimeError("429 Too many requests")) is True

    def test_access_check_challenge_is_transient(self):
        assert (
            _is_transient_error(RuntimeError("check-access-response-enc missing"))
            is True
        )

    def test_account_info_error_is_transient(self):
        assert (
            _is_transient_error(
                RuntimeError("Could not obtain the account information.")
            )
            is True
        )

    def test_ordinary_error_is_not_transient(self):
        assert _is_transient_error(ValueError("invalid input")) is False

    def test_context_length_is_not_transient(self):
        assert (
            _is_transient_error(RuntimeError("maximum context length exceeded"))
            is False
        )


# ── RateLimitRetryConfig ────────────────────────────────────────────────────


class TestRateLimitRetryConfig:
    """Configuration dataclass defaults and env-based construction."""

    def test_defaults(self):
        cfg = RateLimitRetryConfig()
        assert cfg.max_retries == 5
        assert cfg.base_delay_seconds == 2.0
        assert cfg.max_delay_seconds == 30.0

    def test_from_env_uses_defaults_when_unset(self, monkeypatch):
        monkeypatch.delenv("AOAI_429_MAX_RETRIES", raising=False)
        monkeypatch.delenv("AOAI_429_BASE_DELAY_SECONDS", raising=False)
        monkeypatch.delenv("AOAI_429_MAX_DELAY_SECONDS", raising=False)
        cfg = RateLimitRetryConfig.from_env()
        assert cfg.max_retries == 5

    def test_from_env_reads_values(self, monkeypatch):
        monkeypatch.setenv("AOAI_429_MAX_RETRIES", "10")
        monkeypatch.setenv("AOAI_429_BASE_DELAY_SECONDS", "1.5")
        monkeypatch.setenv("AOAI_429_MAX_DELAY_SECONDS", "60.0")
        cfg = RateLimitRetryConfig.from_env()
        assert cfg.max_retries == 10
        assert cfg.base_delay_seconds == 1.5
        assert cfg.max_delay_seconds == 60.0

    def test_from_env_invalid_values_use_defaults(self, monkeypatch):
        monkeypatch.setenv("AOAI_429_MAX_RETRIES", "not_a_number")
        cfg = RateLimitRetryConfig.from_env()
        assert cfg.max_retries == 5
