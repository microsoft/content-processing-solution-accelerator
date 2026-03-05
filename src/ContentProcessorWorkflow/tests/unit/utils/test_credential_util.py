# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for utils/credential_util.py (Azure credential selection)."""

from __future__ import annotations

from utils.credential_util import (
    get_azure_credential,
    get_async_azure_credential,
    validate_azure_authentication,
)


# ── get_azure_credential ─────────────────────────────────────────────────────


class TestGetAzureCredential:
    def test_returns_managed_identity_when_azure_env_detected(self, monkeypatch):
        """When WEBSITE_SITE_NAME is set, should return ManagedIdentityCredential."""
        monkeypatch.setenv("WEBSITE_SITE_NAME", "my-app")
        monkeypatch.delenv("AZURE_CLIENT_ID", raising=False)

        cred = get_azure_credential()
        assert type(cred).__name__ == "ManagedIdentityCredential"

    def test_returns_user_assigned_managed_identity(self, monkeypatch):
        """When AZURE_CLIENT_ID is set, should return user-assigned identity."""
        monkeypatch.setenv("AZURE_CLIENT_ID", "some-client-id")

        cred = get_azure_credential()
        assert type(cred).__name__ == "ManagedIdentityCredential"

    def test_returns_cli_credential_in_local_env(self, monkeypatch):
        """Without Azure env indicators, should try CLI credentials."""
        for var in [
            "WEBSITE_SITE_NAME",
            "AZURE_CLIENT_ID",
            "MSI_ENDPOINT",
            "IDENTITY_ENDPOINT",
            "KUBERNETES_SERVICE_HOST",
            "CONTAINER_REGISTRY_LOGIN",
        ]:
            monkeypatch.delenv(var, raising=False)

        cred = get_azure_credential()
        cred_name = type(cred).__name__
        assert cred_name in (
            "AzureCliCredential",
            "AzureDeveloperCliCredential",
            "DefaultAzureCredential",
        )


# ── get_async_azure_credential ───────────────────────────────────────────────


class TestGetAsyncAzureCredential:
    def test_returns_async_managed_identity_when_azure_env_detected(
        self, monkeypatch
    ):
        monkeypatch.setenv("IDENTITY_ENDPOINT", "http://169.254.169.254")
        monkeypatch.delenv("AZURE_CLIENT_ID", raising=False)

        cred = get_async_azure_credential()
        # The async variant lives in azure.identity.aio (not azure.identity)
        assert ".aio." in type(cred).__module__

    def test_returns_async_cli_in_local_env(self, monkeypatch):
        for var in [
            "WEBSITE_SITE_NAME",
            "AZURE_CLIENT_ID",
            "MSI_ENDPOINT",
            "IDENTITY_ENDPOINT",
            "KUBERNETES_SERVICE_HOST",
            "CONTAINER_REGISTRY_LOGIN",
        ]:
            monkeypatch.delenv(var, raising=False)

        cred = get_async_azure_credential()
        cred_name = type(cred).__name__
        assert cred_name in (
            "AsyncAzureCliCredential",
            "AsyncAzureDeveloperCliCredential",
            "AsyncDefaultAzureCredential",
            "AzureCliCredential",
            "AzureDeveloperCliCredential",
            "DefaultAzureCredential",
        )


# ── validate_azure_authentication ────────────────────────────────────────────


class TestValidateAzureAuthentication:
    def test_local_env_returns_cli_recommendation(self, monkeypatch):
        for var in [
            "WEBSITE_SITE_NAME",
            "AZURE_CLIENT_ID",
            "MSI_ENDPOINT",
            "IDENTITY_ENDPOINT",
            "KUBERNETES_SERVICE_HOST",
        ]:
            monkeypatch.delenv(var, raising=False)

        info = validate_azure_authentication()
        assert info["environment"] == "local_development"
        assert info["credential_type"] == "cli_credentials"
        assert info["status"] in ("configured", "error")

    def test_azure_env_returns_managed_identity_info(self, monkeypatch):
        monkeypatch.setenv("WEBSITE_SITE_NAME", "mysite")
        monkeypatch.delenv("AZURE_CLIENT_ID", raising=False)

        info = validate_azure_authentication()
        assert info["environment"] == "azure_hosted"
        assert info["credential_type"] == "managed_identity"
