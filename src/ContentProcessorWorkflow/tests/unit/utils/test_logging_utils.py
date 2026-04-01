# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for utils/logging_utils.py."""

from __future__ import annotations

import logging

import pytest

from utils.logging_utils import (
    LogMessages,
    _format_specific_error_details,
    configure_application_logging,
    create_migration_logger,
    get_error_details,
    log_error_with_context,
    safe_log,
)


# ── configure_application_logging ────────────────────────────────────────────


class TestConfigureApplicationLogging:
    def test_production_mode_sets_info(self):
        configure_application_logging(debug_mode=False)
        root = logging.getLogger()
        assert root.level == logging.INFO

    def test_debug_mode_sets_debug(self):
        configure_application_logging(debug_mode=True)
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_suppresses_verbose_loggers(self):
        configure_application_logging(debug_mode=False)
        httpx_logger = logging.getLogger("httpx")
        assert httpx_logger.level >= logging.WARNING


# ── create_migration_logger ──────────────────────────────────────────────────


class TestCreateMigrationLogger:
    def test_creates_logger_with_handler(self):
        logger = create_migration_logger("test_logger_unique_1")
        assert logger.name == "test_logger_unique_1"
        assert len(logger.handlers) >= 1
        assert logger.level == logging.INFO

    def test_custom_level(self):
        logger = create_migration_logger("test_logger_unique_2", level=logging.DEBUG)
        assert logger.level == logging.DEBUG

    def test_idempotent_handler_attachment(self):
        name = "test_logger_unique_3"
        logger1 = create_migration_logger(name)
        count1 = len(logger1.handlers)
        logger2 = create_migration_logger(name)
        assert len(logger2.handlers) == count1


# ── safe_log ─────────────────────────────────────────────────────────────────


class TestSafeLog:
    def test_logs_formatted_message(self, caplog):
        logger = logging.getLogger("safe_log_test")
        with caplog.at_level(logging.INFO, logger="safe_log_test"):
            safe_log(logger, "info", "Hello {name}", name="World")
        assert "Hello World" in caplog.text

    def test_handles_dict_kwargs(self, caplog):
        logger = logging.getLogger("safe_log_dict")
        with caplog.at_level(logging.INFO, logger="safe_log_dict"):
            safe_log(logger, "info", "Data: {data}", data={"key": "value"})
        assert "Data:" in caplog.text

    def test_raises_on_format_failure(self):
        logger = logging.getLogger("safe_log_fail")
        with pytest.raises(RuntimeError, match="Safe logger format failure"):
            safe_log(logger, "info", "Missing {unknown_var}")


# ── get_error_details ────────────────────────────────────────────────────────


class TestGetErrorDetails:
    def test_basic_exception(self):
        try:
            raise ValueError("test error")
        except ValueError as e:
            details = get_error_details(e)

        assert details["exception_type"] == "ValueError"
        assert details["exception_message"] == "test error"
        assert details["exception_cause"] is None

    def test_chained_exception(self):
        try:
            try:
                raise OSError("disk full")
            except OSError as inner:
                raise RuntimeError("write failed") from inner
        except RuntimeError as e:
            details = get_error_details(e)

        assert details["exception_type"] == "RuntimeError"
        assert "disk full" in details["exception_cause"]


# ── _format_specific_error_details ───────────────────────────────────────────


class TestFormatSpecificErrorDetails:
    def test_empty_details_returns_empty(self):
        assert _format_specific_error_details({}) == ""

    def test_http_details(self):
        details = {"http_status_code": 500, "http_reason": "Internal Server Error"}
        result = _format_specific_error_details(details)
        assert "500" in result
        assert "Internal Server Error" in result


# ── log_error_with_context ───────────────────────────────────────────────────


class TestLogErrorWithContext:
    def test_logs_and_returns_details(self, caplog):
        logger = logging.getLogger("error_ctx_test")
        try:
            raise ValueError("boom")
        except ValueError as e:
            with caplog.at_level(logging.ERROR, logger="error_ctx_test"):
                details = log_error_with_context(logger, e, context="TestOp")

        assert details["exception_type"] == "ValueError"
        assert "boom" in caplog.text


# ── LogMessages ──────────────────────────────────────────────────────────────


class TestLogMessages:
    def test_templates_are_formattable(self):
        msg = LogMessages.ERROR_STEP_FAILED.format(step="extraction", error="timeout")
        assert "extraction" in msg
        assert "timeout" in msg

    def test_success_template(self):
        msg = LogMessages.SUCCESS_COMPLETED.format(operation="summarize", details="ok")
        assert "summarize" in msg
