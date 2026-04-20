"""Extended tests for azure_credential_utils.py to improve coverage"""
from unittest.mock import Mock, patch
from libs.utils.azure_credential_utils import (
    get_azure_credential,
    get_async_azure_credential,
    get_bearer_token_provider,
    get_async_bearer_token_provider,
    validate_azure_authentication
)


class TestAzureCredentialUtilsExtended:
    """Extended test suite for Azure credential utilities"""

    def test_get_azure_credential_with_azure_client_id(self, monkeypatch):
        """Test credential creation with user-assigned managed identity"""
        monkeypatch.setenv("AZURE_CLIENT_ID", "test-client-id-123")
        monkeypatch.setenv("MSI_ENDPOINT", "http://169.254.169.254/metadata/identity")

        with patch('libs.utils.azure_credential_utils.ManagedIdentityCredential') as mock_cred:
            mock_instance = Mock()
            mock_cred.return_value = mock_instance

            credential = get_azure_credential()

            mock_cred.assert_called_once_with(client_id="test-client-id-123")
            assert credential == mock_instance

    def test_get_azure_credential_with_website_site_name(self, monkeypatch):
        """Test credential creation in Azure App Service"""
        monkeypatch.setenv("WEBSITE_SITE_NAME", "my-app-service")
        monkeypatch.delenv("AZURE_CLIENT_ID", raising=False)

        with patch('libs.utils.azure_credential_utils.ManagedIdentityCredential') as mock_cred:
            mock_instance = Mock()
            mock_cred.return_value = mock_instance

            credential = get_azure_credential()

            mock_cred.assert_called_once_with()
            assert credential == mock_instance

    def test_get_azure_credential_cli_failure_fallback(self, monkeypatch):
        """Test fallback to DefaultAzureCredential when CLI credentials fail"""
        # Clear all Azure environment indicators
        for key in ["WEBSITE_SITE_NAME", "AZURE_CLIENT_ID", "MSI_ENDPOINT",
                    "IDENTITY_ENDPOINT", "KUBERNETES_SERVICE_HOST", "CONTAINER_REGISTRY_LOGIN"]:
            monkeypatch.delenv(key, raising=False)

        with patch('libs.utils.azure_credential_utils.AzureCliCredential') as mock_cli_cred, \
             patch('libs.utils.azure_credential_utils.AzureDeveloperCliCredential') as mock_azd_cred, \
             patch('libs.utils.azure_credential_utils.DefaultAzureCredential') as mock_default:

            # Make both CLI credentials raise exceptions
            mock_cli_cred.side_effect = Exception("CLI credential failed")
            mock_azd_cred.side_effect = Exception("AZD credential failed")
            mock_default_instance = Mock()
            mock_default.return_value = mock_default_instance

            credential = get_azure_credential()

            assert credential == mock_default_instance
            mock_default.assert_called_once()

    def test_get_azure_credential_azd_success(self, monkeypatch):
        """Test successful Azure Developer CLI credential"""
        for key in ["WEBSITE_SITE_NAME", "AZURE_CLIENT_ID", "MSI_ENDPOINT"]:
            monkeypatch.delenv(key, raising=False)

        with patch('libs.utils.azure_credential_utils.AzureCliCredential') as mock_cli_cred, \
             patch('libs.utils.azure_credential_utils.AzureDeveloperCliCredential') as mock_azd_cred:

            # Make CLI fail but AZD succeed
            mock_cli_cred.side_effect = Exception("CLI failed")
            mock_azd_instance = Mock()
            mock_azd_cred.return_value = mock_azd_instance

            credential = get_azure_credential()

            assert credential == mock_azd_instance

    def test_get_async_azure_credential_with_client_id(self, monkeypatch):
        """Test async credential with user-assigned managed identity"""
        monkeypatch.setenv("AZURE_CLIENT_ID", "async-client-id")
        monkeypatch.setenv("MSI_ENDPOINT", "http://localhost")

        with patch('libs.utils.azure_credential_utils.AsyncManagedIdentityCredential') as mock_cred:
            mock_instance = Mock()
            mock_cred.return_value = mock_instance

            credential = get_async_azure_credential()

            mock_cred.assert_called_once_with(client_id="async-client-id")
            assert credential == mock_instance

    def test_get_async_azure_credential_system_identity(self, monkeypatch):
        """Test async credential with system-assigned managed identity"""
        monkeypatch.setenv("IDENTITY_ENDPOINT", "http://localhost")
        monkeypatch.delenv("AZURE_CLIENT_ID", raising=False)

        with patch('libs.utils.azure_credential_utils.AsyncManagedIdentityCredential') as mock_cred:
            mock_instance = Mock()
            mock_cred.return_value = mock_instance

            credential = get_async_azure_credential()

            mock_cred.assert_called_once_with()
            assert credential == mock_instance

    def test_get_async_azure_credential_cli_fallback(self, monkeypatch):
        """Test async credential fallback to DefaultAzureCredential"""
        for key in ["WEBSITE_SITE_NAME", "AZURE_CLIENT_ID", "MSI_ENDPOINT",
                    "IDENTITY_ENDPOINT", "KUBERNETES_SERVICE_HOST"]:
            monkeypatch.delenv(key, raising=False)

        with patch('libs.utils.azure_credential_utils.AsyncAzureCliCredential') as mock_cli, \
             patch('libs.utils.azure_credential_utils.AsyncAzureDeveloperCliCredential') as mock_azd, \
             patch('libs.utils.azure_credential_utils.AsyncDefaultAzureCredential') as mock_default:

            mock_cli.side_effect = Exception("Async CLI failed")
            mock_azd.side_effect = Exception("Async AZD failed")
            mock_default_instance = Mock()
            mock_default.return_value = mock_default_instance

            credential = get_async_azure_credential()

            assert credential == mock_default_instance

    def test_get_bearer_token_provider_success(self, monkeypatch):
        """Test bearer token provider creation"""
        monkeypatch.setenv("MSI_ENDPOINT", "http://localhost")

        with patch('libs.utils.azure_credential_utils.get_azure_credential') as mock_get_cred, \
             patch('libs.utils.azure_credential_utils.identity_get_bearer_token_provider') as mock_provider:

            mock_credential = Mock()
            mock_get_cred.return_value = mock_credential
            mock_token_provider = Mock()
            mock_provider.return_value = mock_token_provider

            result = get_bearer_token_provider()

            mock_get_cred.assert_called_once()
            mock_provider.assert_called_once_with(
                mock_credential,
                "https://cognitiveservices.azure.com/.default"
            )
            assert result == mock_token_provider

    @pytest.mark.asyncio
    async def test_get_async_bearer_token_provider_success(self, monkeypatch):
        """Test async bearer token provider creation"""
        monkeypatch.setenv("MSI_ENDPOINT", "http://localhost")

        # Create an async mock
        from unittest.mock import AsyncMock

        with patch('libs.utils.azure_credential_utils.get_async_azure_credential', new_callable=AsyncMock) as mock_get_cred, \
             patch('libs.utils.azure_credential_utils.identity_get_async_bearer_token_provider') as mock_provider:

            mock_credential = Mock()
            mock_get_cred.return_value = mock_credential
            mock_token_provider = Mock()
            mock_provider.return_value = mock_token_provider

            result = await get_async_bearer_token_provider()

            mock_get_cred.assert_called_once()
            mock_provider.assert_called_once_with(
                mock_credential,
                "https://cognitiveservices.azure.com/.default"
            )
            assert result == mock_token_provider

    def test_validate_azure_authentication_managed_identity(self, monkeypatch):
        """Test validation with managed identity environment"""
        monkeypatch.setenv("MSI_ENDPOINT", "http://localhost")
        monkeypatch.setenv("AZURE_CLIENT_ID", "test-client-id")

        with patch('libs.utils.azure_credential_utils.get_azure_credential') as mock_get_cred:
            # Use Mock instead of actual ManagedIdentityCredential
            mock_credential = Mock()
            mock_credential.__class__.__name__ = "ManagedIdentityCredential"
            mock_get_cred.return_value = mock_credential

            result = validate_azure_authentication()

            assert result["status"] == "configured"
            assert result["environment"] == "azure_hosted"
            assert result["credential_type"] == "managed_identity"
            assert "AZURE_CLIENT_ID" in result["azure_env_indicators"]
            assert "user-assigned" in result["recommendations"][0]

    def test_validate_azure_authentication_local_dev(self, monkeypatch):
        """Test validation in local development environment"""
        for key in ["WEBSITE_SITE_NAME", "AZURE_CLIENT_ID", "MSI_ENDPOINT",
                    "IDENTITY_ENDPOINT", "KUBERNETES_SERVICE_HOST"]:
            monkeypatch.delenv(key, raising=False)

        with patch('libs.utils.azure_credential_utils.get_azure_credential') as mock_get_cred:
            from azure.identity import DefaultAzureCredential
            mock_credential = DefaultAzureCredential()
            mock_get_cred.return_value = mock_credential

            result = validate_azure_authentication()

            assert result["status"] == "configured"
            assert result["environment"] == "local_development"
            assert result["credential_type"] == "cli_credentials"
            assert any("azd auth login" in rec for rec in result["recommendations"])

    def test_validate_azure_authentication_error(self, monkeypatch):
        """Test validation when credential creation fails"""
        for key in ["WEBSITE_SITE_NAME", "AZURE_CLIENT_ID", "MSI_ENDPOINT"]:
            monkeypatch.delenv(key, raising=False)

        with patch('libs.utils.azure_credential_utils.get_azure_credential') as mock_get_cred:
            mock_get_cred.side_effect = Exception("Credential creation failed")

            result = validate_azure_authentication()

            assert result["status"] == "error"
            assert "error" in result
            assert "Credential creation failed" in result["error"]

    def test_validate_azure_authentication_kubernetes(self, monkeypatch):
        """Test validation in Kubernetes environment"""
        monkeypatch.setenv("KUBERNETES_SERVICE_HOST", "10.0.0.1")
        monkeypatch.delenv("AZURE_CLIENT_ID", raising=False)

        with patch('libs.utils.azure_credential_utils.get_azure_credential') as mock_get_cred:
            mock_credential = Mock()
            mock_get_cred.return_value = mock_credential

            result = validate_azure_authentication()

            assert result["environment"] == "azure_hosted"
            assert result["credential_type"] == "managed_identity"
            assert "KUBERNETES_SERVICE_HOST" in result["azure_env_indicators"]
            assert "system-assigned" in result["recommendations"][0]
