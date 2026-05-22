# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs.base.application_models (shared Pydantic base classes)."""

from __future__ import annotations

import pytest
from pydantic import Field, ValidationError

from libs.base.application_models import AppModelBase, ModelBaseSettings

# ── TestAppModelBase ────────────────────────────────────────────────────


class TestAppModelBase:
    """Base model config: populate_by_name, arbitrary_types, validate_assignment."""

    def test_subclass_construction(self):
        class _Sample(AppModelBase):
            name: str
            count: int = 0

        obj = _Sample(name="test", count=5)
        assert obj.name == "test"
        assert obj.count == 5

    def test_validate_assignment(self):
        class _Strict(AppModelBase):
            value: int = 0

        obj = _Strict(value=1)
        with pytest.raises(ValidationError):
            obj.value = "not-an-int"

    def test_populate_by_name(self):
        class _Aliased(AppModelBase):
            my_field: str = Field(default="x", alias="myField")

        obj = _Aliased(my_field="hello")
        assert obj.my_field == "hello"

    def test_arbitrary_types_allowed(self):
        class _Custom:
            pass

        class _Model(AppModelBase):
            obj: _Custom

        instance = _Custom()
        m = _Model(obj=instance)
        assert m.obj is instance


# ── TestModelBaseSettings ───────────────────────────────────────────────


class TestModelBaseSettings:
    """Base settings model ignores extra fields and is case-insensitive."""

    def test_ignores_extra_fields(self):
        class _Cfg(ModelBaseSettings):
            known: str = "default"

        cfg = _Cfg(known="value", unknown="ignored")
        assert cfg.known == "value"
        assert not hasattr(cfg, "unknown")
