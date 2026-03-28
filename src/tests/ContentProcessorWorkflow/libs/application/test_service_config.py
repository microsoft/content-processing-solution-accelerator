# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
from __future__ import annotations

"""Unit tests for ServiceConfig."""

from libs.application.service_config import ServiceConfig


def test_service_config_valid_with_entra_id_requires_endpoint_and_chat_deployment() -> (
    None
):
    env = {
        "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com",
        "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME": "chat",
    }
    cfg = ServiceConfig("default", "AZURE_OPENAI", env, use_entra_id=True)
    assert cfg.is_valid() is True


def test_service_config_api_key_mode_requires_api_key() -> None:
    env = {
        "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com",
        "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME": "chat",
        # Intentionally missing API_KEY
    }
    cfg = ServiceConfig("default", "AZURE_OPENAI", env, use_entra_id=False)
    assert cfg.is_valid() is False

    env["AZURE_OPENAI_API_KEY"] = "secret"
    cfg2 = ServiceConfig("default", "AZURE_OPENAI", env, use_entra_id=False)
    assert cfg2.is_valid() is True


def test_service_config_to_dict_converts_empty_strings_to_none() -> None:
    env = {
        "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com",
        "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME": "chat",
        "AZURE_OPENAI_API_VERSION": "",
    }
    cfg = ServiceConfig("default", "AZURE_OPENAI", env, use_entra_id=True)
    d = cfg.to_dict()
    assert d["endpoint"] == "https://example.openai.azure.com"
    assert d["chat_deployment_name"] == "chat"
    assert d["api_version"] is None
