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


def test_configuration_logging_fields(monkeypatch) -> None:
    monkeypatch.setenv("AZURE_PACKAGE_LOGGING_LEVEL", "ERROR")
    monkeypatch.setenv("AZURE_LOGGING_PACKAGES", "azure.core,azure.storage")
    cfg = Configuration()
    assert cfg.azure_package_logging_level == "ERROR"
    assert cfg.azure_logging_packages == "azure.core,azure.storage"
