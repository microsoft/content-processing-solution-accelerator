# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
from __future__ import annotations

"""Unit tests for ApplicationBase."""

from libs.base.application_base import ApplicationBase


def test_ApplicationBase():
    assert ApplicationBase.run is not None
    assert ApplicationBase.__init__ is not None
    assert ApplicationBase._load_env is not None
    assert ApplicationBase._get_derived_class_location is not None
