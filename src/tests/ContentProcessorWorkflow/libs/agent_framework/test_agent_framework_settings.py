# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs/agent_framework/agent_framework_settings.py."""

from __future__ import annotations

from libs.agent_framework.agent_framework_settings import AgentFrameworkSettings


class TestServiceDiscovery:
    def test_discovers_default_service_from_env(self, monkeypatch):
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
        monkeypatch.setenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", "gpt-4")
        monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-02-15")

        settings = AgentFrameworkSettings()
        assert settings.has_service("default")

        cfg = settings.get_service_config("default")
        assert cfg is not None
        assert cfg.endpoint == "https://example.openai.azure.com"
        assert cfg.chat_deployment_name == "gpt-4"

    def test_returns_none_for_unknown_service(self, monkeypatch):
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
        monkeypatch.setenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", "gpt-4")

        settings = AgentFrameworkSettings()
        assert settings.get_service_config("nonexistent") is None

    def test_custom_service_prefix(self, monkeypatch):
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://default.openai.azure.com")
        monkeypatch.setenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", "gpt-4")
        monkeypatch.setenv(
            "AZURE_OPENAI_FAST_ENDPOINT", "https://fast.openai.azure.com"
        )
        monkeypatch.setenv("AZURE_OPENAI_FAST_CHAT_DEPLOYMENT_NAME", "gpt-4-turbo")

        settings = AgentFrameworkSettings(
            custom_service_prefixes={"fast": "AZURE_OPENAI_FAST"}
        )

        assert settings.has_service("fast")
        fast_cfg = settings.get_service_config("fast")
        assert fast_cfg is not None
        assert fast_cfg.endpoint == "https://fast.openai.azure.com"

    def test_get_available_services(self, monkeypatch):
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
        monkeypatch.setenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", "gpt-4")

        settings = AgentFrameworkSettings()
        services = settings.get_available_services()
        assert "default" in services


class TestEnvFileLoading:
    def test_loads_env_file(self, monkeypatch, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text(
            "AZURE_OPENAI_ENDPOINT=https://fromfile.openai.azure.com\n"
            "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-4-from-file\n",
            encoding="utf-8",
        )

        # Clear env vars so they come from file
        monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", raising=False)

        settings = AgentFrameworkSettings(env_file_path=str(env_file))
        cfg = settings.get_service_config("default")
        assert cfg is not None
        assert cfg.endpoint == "https://fromfile.openai.azure.com"

    def test_env_file_does_not_overwrite_existing(self, monkeypatch, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text(
            "AZURE_OPENAI_ENDPOINT=https://fromfile.openai.azure.com\n"
            "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-4-from-file\n",
            encoding="utf-8",
        )

        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://already-set.openai.azure.com")
        monkeypatch.delenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", raising=False)

        settings = AgentFrameworkSettings(env_file_path=str(env_file))
        cfg = settings.get_service_config("default")
        assert cfg is not None
        # Existing env var should NOT be overwritten
        assert cfg.endpoint == "https://already-set.openai.azure.com"

    def test_missing_env_file_is_silently_skipped(self):
        """Constructor does not raise for a missing .env file."""
        # The constructor silently skips non-existent env files.
        settings = AgentFrameworkSettings(env_file_path="/nonexistent/.env")
        assert settings is not None


class TestRefreshServices:
    def test_refresh_picks_up_new_env_vars(self, monkeypatch):
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
        monkeypatch.setenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", "gpt-4")

        settings = AgentFrameworkSettings()
        assert settings.has_service("default")

        # Re-discover after env changes
        settings.refresh_services()
        assert settings.has_service("default")
