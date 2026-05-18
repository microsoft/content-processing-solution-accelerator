# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs.application.service_config (LLM service configuration)."""

from __future__ import annotations

from libs.application.service_config import ServiceConfig

# ── TestServiceConfig ───────────────────────────────────────────────────


class TestServiceConfig:
    """Construction, validation, and serialisation of ServiceConfig."""

    def _make_env(self, **overrides):
        base = {
            "AZURE_OPENAI_API_VERSION": "2024-02-01",
            "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME": "gpt-4",
            "AZURE_OPENAI_ENDPOINT": "https://myoai.openai.azure.com",
            "AZURE_OPENAI_API_KEY": "secret-key",
        }
        base.update(overrides)
        return base

    def test_construction_from_env_vars(self):
        env = self._make_env()
        cfg = ServiceConfig("default", "AZURE_OPENAI", env)
        assert cfg.service_id == "default"
        assert cfg.api_version == "2024-02-01"
        assert cfg.chat_deployment_name == "gpt-4"
        assert cfg.endpoint == "https://myoai.openai.azure.com"

    def test_is_valid_with_entra_id(self):
        env = self._make_env()
        cfg = ServiceConfig("svc", "AZURE_OPENAI", env, use_entra_id=True)
        assert cfg.is_valid() is True

    def test_is_valid_without_entra_id_requires_api_key(self):
        env = self._make_env()
        cfg = ServiceConfig("svc", "AZURE_OPENAI", env, use_entra_id=False)
        assert cfg.is_valid() is True

    def test_is_invalid_missing_endpoint(self):
        env = self._make_env()
        del env["AZURE_OPENAI_ENDPOINT"]
        cfg = ServiceConfig("svc", "AZURE_OPENAI", env, use_entra_id=True)
        assert cfg.is_valid() is False

    def test_is_invalid_missing_deployment(self):
        env = self._make_env()
        del env["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"]
        cfg = ServiceConfig("svc", "AZURE_OPENAI", env, use_entra_id=True)
        assert cfg.is_valid() is False

    def test_is_invalid_no_entra_no_key(self):
        env = self._make_env()
        del env["AZURE_OPENAI_API_KEY"]
        cfg = ServiceConfig("svc", "AZURE_OPENAI", env, use_entra_id=False)
        assert cfg.is_valid() is False

    def test_to_dict_keys(self):
        env = self._make_env()
        cfg = ServiceConfig("svc", "AZURE_OPENAI", env)
        d = cfg.to_dict()
        assert d["endpoint"] == "https://myoai.openai.azure.com"
        assert d["chat_deployment_name"] == "gpt-4"
        assert d["api_key"] == "secret-key"

    def test_to_dict_empty_fields_become_none(self):
        cfg = ServiceConfig("svc", "MISSING_PREFIX", {})
        d = cfg.to_dict()
        assert d["endpoint"] is None
        assert d["chat_deployment_name"] is None

    def test_custom_prefix(self):
        env = {
            "MY_LLM_ENDPOINT": "https://custom.api",
            "MY_LLM_CHAT_DEPLOYMENT_NAME": "model-v2",
        }
        cfg = ServiceConfig("custom", "MY_LLM", env, use_entra_id=True)
        assert cfg.endpoint == "https://custom.api"
        assert cfg.chat_deployment_name == "model-v2"
        assert cfg.is_valid() is True
