# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs.pipeline.entities.pipeline_message_base (exception serialisation)."""

from __future__ import annotations

from libs.pipeline.entities.pipeline_message_base import (
    PipelineMessageBase,
    SerializableException,
)

# ── TestSerializableException ───────────────────────────────────────────


class TestSerializableException:
    """Exception model defaults and field storage."""

    def test_defaults(self):
        exc = SerializableException()
        assert exc.exception is None
        assert exc.exception_details is None

    def test_all_fields(self):
        exc = SerializableException(
            exception="ValueError",
            exception_details="bad value",
            exception_type="ValueError",
            exception_message="bad value",
        )
        assert exc.exception == "ValueError"
        assert exc.exception_message == "bad value"


# ── TestPipelineMessageBase ─────────────────────────────────────────────


class TestPipelineMessageBase:
    """Exception attachment and property access."""

    def _make_concrete(self):
        class _Concrete(PipelineMessageBase):
            def save_to_persistent_storage(self, account_url, container_name):
                pass

        return _Concrete()

    def test_exception_defaults_to_none(self):
        obj = self._make_concrete()
        assert obj.exception is None

    def test_add_exception(self):
        obj = self._make_concrete()
        try:
            raise ValueError("test error")
        except ValueError as e:
            obj.add_exception(e)

        assert obj.exception is not None
        assert obj.exception.exception == "ValueError"
        assert obj.exception.exception_message == "test error"

    def test_exception_setter(self):
        obj = self._make_concrete()
        try:
            raise RuntimeError("boom")
        except RuntimeError as e:
            obj.exception = e

        assert obj.exception.exception_type == "RuntimeError"

    def test_add_exception_with_cause(self):
        obj = self._make_concrete()
        try:
            try:
                raise OSError("disk full")
            except OSError:
                raise IOError("write failed") from OSError("disk full")
        except IOError as e:
            obj.add_exception(e)

        assert obj.exception.exception_inner_exception is not None
