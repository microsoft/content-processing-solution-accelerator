# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
from __future__ import annotations

"""Unit tests for Azure App Configuration helper."""

from dataclasses import dataclass

import pytest


@dataclass
class _FakeSetting:
    key: str
    value: str


class _FakeAppConfigClient:
    def __init__(self, endpoint: str, credential: object):
        self.endpoint = endpoint
        self.credential = credential
        self._settings: list[_FakeSetting] = []

    def list_configuration_settings(self):
        return list(self._settings)


def test_app_configuration_helper_initializes_client(monkeypatch) -> None:
    from libs.azure import app_configuration as mod

    def _factory(endpoint: str, credential: object):
        # Return a new fake client each time so the test can assert endpoint wiring.
        return _FakeAppConfigClient(endpoint, credential)

    monkeypatch.setattr(mod, "AzureAppConfigurationClient", _factory)

    helper = mod.AppConfigurationHelper(
        "https://appconfig.example", credential=object()
    )

    assert helper.app_config_client is not None
    assert helper.app_config_client.endpoint == "https://appconfig.example"


def test_initialize_client_raises_when_endpoint_missing() -> None:
    from libs.azure.app_configuration import AppConfigurationHelper

    helper = AppConfigurationHelper.__new__(AppConfigurationHelper)
    helper.app_config_endpoint = None
    helper.credential = object()

    with pytest.raises(ValueError, match="Endpoint is not set"):
        helper._initialize_client()


def test_initialize_client_raises_when_credential_missing() -> None:
    from libs.azure.app_configuration import AppConfigurationHelper

    helper = AppConfigurationHelper.__new__(AppConfigurationHelper)
    helper.app_config_endpoint = "https://appconfig.example"
    helper.credential = None

    with pytest.raises(ValueError, match="credential is not set"):
        helper._initialize_client()


def test_read_configuration_raises_when_client_not_initialized() -> None:
    from libs.azure.app_configuration import AppConfigurationHelper

    helper = AppConfigurationHelper.__new__(AppConfigurationHelper)
    helper.app_config_client = None

    with pytest.raises(ValueError, match="client is not initialized"):
        helper.read_configuration()


def test_read_and_set_environmental_variables_sets_os_environ(monkeypatch) -> None:
    from libs.azure import app_configuration as mod

    fake = _FakeAppConfigClient("https://appconfig.example", object())
    fake._settings = [
        _FakeSetting("K1", "V1"),
        _FakeSetting("K2", "V2"),
    ]

    def _factory(endpoint: str, credential: object):
        return fake

    monkeypatch.setattr(mod, "AzureAppConfigurationClient", _factory)

    helper = mod.AppConfigurationHelper(
        "https://appconfig.example", credential=object()
    )

    # Ensure we don't leak env changes between tests.
    monkeypatch.delenv("K1", raising=False)
    monkeypatch.delenv("K2", raising=False)

    env = helper.read_and_set_environmental_variables()

    assert env["K1"] == "V1"
    assert env["K2"] == "V2"
