# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
from __future__ import annotations

"""Unit tests for AppConfiguration helper."""

from libs.application.application_configuration import Configuration


def test_configuration_defaults():
    cfg = Configuration()
    assert cfg.azure_package_logging_level == "WARNING"
    assert cfg.storage_queue_name == "processes-queue"
