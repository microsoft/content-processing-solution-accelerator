# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
from __future__ import annotations

"""Unit tests for environment-based configuration loading."""

import pytest


def test_env_configuration_reads_app_config_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from libs.application.application_configuration import _envConfiguration

    monkeypatch.setenv("APP_CONFIG_ENDPOINT", "https://appconfig.example")

    cfg = _envConfiguration()

    assert cfg.app_config_endpoint == "https://appconfig.example"
