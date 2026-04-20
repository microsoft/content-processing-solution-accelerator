# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
from __future__ import annotations

"""Unit tests for ApplicationConfiguration."""

from libs.application.application_configuration import Configuration


def test_configuration_reads_alias_env_vars(monkeypatch) -> None:
    monkeypatch.setenv("APP_COSMOS_CONNSTR", "https://cosmos.example")
    monkeypatch.setenv("APP_COSMOS_DATABASE", "db1")
    monkeypatch.setenv("APP_COSMOS_CONTAINER_BATCH_PROCESS", "c1")
    monkeypatch.setenv("STORAGE_QUEUE_NAME", "q1")

    cfg = Configuration()
    assert cfg.app_cosmos_connstr == "https://cosmos.example"
    assert cfg.app_cosmos_database == "db1"
    assert cfg.app_cosmos_container_batch_process == "c1"
    assert cfg.storage_queue_name == "q1"


def test_configuration_boolean_parsing(monkeypatch) -> None:
    # pydantic-settings parses common truthy strings.
    monkeypatch.setenv("APP_LOGGING_ENABLE", "true")
    cfg = Configuration()
    assert cfg.app_logging_enable is True
