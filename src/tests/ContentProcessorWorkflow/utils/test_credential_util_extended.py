"""Extended tests for credential_util.py to improve coverage"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from utils.credential_util import (
    get_azure_credential,
    get_async_azure_credential,
    get_bearer_token_provider,
    validate_azure_authentication
)


class TestCredentialUtilExtended:
    """Extended test suite for credential utility functions"""
    
    def test_get_azure_credential_with_user_assigned_identity(self, monkeypatch):
        """Test credential with user-assigned managed identity"""
        monkeypatch.setenv("AZURE_CLIENT_ID", "user-assigned-id-456")
        monkeypatch.setenv("IDENTITY_ENDPOINT", "http://169.254.169.254")
        
        with patch('utils.credential_util.ManagedIdentityCredential') as mock_cred:
            mock_instance = Mock()
            mock_cred.return_value = mock_instance
            
            credential = get_azure_credential()
            
            mock_cred.assert_called_once_with(client_id="user-assigned-id-456")
            assert credential == mock_instance
    
    def test_get_azure_credential_app_service_environment(self, monkeypatch):
        """Test credential in Azure App Service"""
        monkeypatch.setenv("WEBSITE_SITE_NAME", "test-app-service")
        monkeypatch.delenv("AZURE_CLIENT_ID", raising=False)
        
        with patch('utils.credential_util.ManagedIdentityCredential') as mock_cred:
            mock_instance = Mock()
            mock_cred.return_value = mock_instance
            
            credential = get_azure_credential()
            
            mock_cred.assert_called_once_with()
            assert credential == mock_instance
    
    def test_get_azure_credential_all_cli_fail(self, monkeypatch):
        """Test fallback when all CLI credentials fail"""
        for key in ["WEBSITE_SITE_NAME", "AZURE_CLIENT_ID", "MSI_ENDPOINT", 
                    "IDENTITY_ENDPOINT", "KUBERNETES_SERVICE_HOST", "CONTAINER_REGISTRY_LOGIN"]:
            monkeypatch.delenv(key, raising=False)
        
        with patch('utils.credential_util.AzureCliCredential') as mock_cli, \
             patch('utils.credential_util.AzureDeveloperCliCredential') as mock_azd, \
             patch('utils.credential_util.DefaultAzureCredential') as mock_default:
            
            mock_cli.side_effect = Exception("AzureCLI not available")
            mock_azd.side_effect = Exception("AzureDeveloperCLI not available")
            mock_default_instance = Mock()
            mock_default.return_value = mock_default_instance
            
            credential = get_azure_credential()
            
            assert credential == mock_default_instance
            mock_default.assert_called_once()
    
    def test_get_azure_credential_cli_success(self, monkeypatch):
        """Test successful Azure CLI credential"""
        for key in ["WEBSITE_SITE_NAME", "AZURE_CLIENT_ID", "MSI_ENDPOINT"]:
            monkeypatch.delenv(key, raising=False)
        
        with patch('utils.credential_util.AzureCliCredential') as mock_cli:
            mock_cli_instance = Mock()
            mock_cli.return_value = mock_cli_instance
            
            credential = get_azure_credential()
            
            assert credential == mock_cli_instance
    
    def test_get_azure_credential_azd_success_after_cli_fail(self, monkeypatch):
        """Test AZD credential when Azure CLI fails"""
        for key in ["WEBSITE_SITE_NAME", "AZURE_CLIENT_ID"]:
            monkeypatch.delenv(key, raising=False)
        
        with patch('utils.credential_util.AzureCliCredential') as mock_cli, \
             patch('utils.credential_util.AzureDeveloperCliCredential') as mock_azd:
            
            mock_cli.side_effect = Exception("CLI not found")
            mock_azd_instance = Mock()
            mock_azd.return_value = mock_azd_instance
            
            credential = get_azure_credential()
            
            assert credential == mock_azd_instance
    
    def test_get_async_azure_credential_with_client_id(self, monkeypatch):
        """Test async credential with client ID"""
        monkeypatch.setenv("AZURE_CLIENT_ID", "async-client-123")
        monkeypatch.setenv("MSI_ENDPOINT", "http://localhost")
        
        with patch('utils.credential_util.AsyncManagedIdentityCredential') as mock_cred:
            mock_instance = Mock()
            mock_cred.return_value = mock_instance
            
            credential = get_async_azure_credential()
            
            mock_cred.assert_called_once_with(client_id="async-client-123")
            assert credential == mock_instance
    
    def test_get_async_azure_credential_kubernetes(self, monkeypatch):
        """Test async credential in Kubernetes"""
        monkeypatch.setenv("KUBERNETES_SERVICE_HOST", "10.0.0.1")
        monkeypatch.delenv("AZURE_CLIENT_ID", raising=False)
        
        with patch('utils.credential_util.AsyncManagedIdentityCredential') as mock_cred:
            mock_instance = Mock()
            mock_cred.return_value = mock_instance
            
            credential = get_async_azure_credential()
            
            mock_cred.assert_called_once_with()
            assert credential == mock_instance
    
    def test_get_async_azure_credential_cli_fallback(self, monkeypatch):
        """Test async fallback to DefaultAzureCredential"""
        for key in ["WEBSITE_SITE_NAME", "AZURE_CLIENT_ID", "MSI_ENDPOINT"]:
            monkeypatch.delenv(key, raising=False)
        
        with patch('utils.credential_util.AsyncAzureCliCredential') as mock_cli, \
             patch('utils.credential_util.AsyncAzureDeveloperCliCredential') as mock_azd, \
             patch('utils.credential_util.AsyncDefaultAzureCredential') as mock_default:
            
            mock_cli.side_effect = Exception("Async CLI failed")
            mock_azd.side_effect = Exception("Async AZD failed")
            mock_default_instance = Mock()
            mock_default.return_value = mock_default_instance
            
            credential = get_async_azure_credential()
            
            assert credential == mock_default_instance
    
    def test_get_async_azure_credential_azd_success(self, monkeypatch):
        """Test async AZD credential success"""
        for key in ["WEBSITE_SITE_NAME", "AZURE_CLIENT_ID", "MSI_ENDPOINT"]:
            monkeypatch.delenv(key, raising=False)
        
        with patch('utils.credential_util.AsyncAzureCliCredential') as mock_cli, \
             patch('utils.credential_util.AsyncAzureDeveloperCliCredential') as mock_azd:
            
            mock_cli.side_effect = Exception("CLI failed")
            mock_azd_instance = Mock()
            mock_azd.return_value = mock_azd_instance
            
            credential = get_async_azure_credential()
            
            assert credential == mock_azd_instance
    
    def test_get_bearer_token_provider_creates_provider(self, monkeypatch):
        """Test bearer token provider creation"""
        monkeypatch.setenv("MSI_ENDPOINT", "http://localhost")
        
        with patch('utils.credential_util.get_azure_credential') as mock_get_cred, \
             patch('utils.credential_util.identity_get_bearer_token_provider') as mock_provider:
            
            mock_credential = Mock()
            mock_get_cred.return_value = mock_credential
            mock_token_provider = Mock()
            mock_provider.return_value = mock_token_provider
            
            result = get_bearer_token_provider()
            
            mock_get_cred.assert_called_once()
            mock_provider.assert_called_once()
            assert result == mock_token_provider
    
    def test_validate_azure_authentication_managed_identity_user_assigned(self, monkeypatch):
        """Test validation with user-assigned managed identity"""
        monkeypatch.setenv("MSI_ENDPOINT", "http://localhost")
        monkeypatch.setenv("AZURE_CLIENT_ID", "user-id-789")
        
        with patch('utils.credential_util.get_azure_credential') as mock_get_cred:
            mock_credential = Mock()
            mock_get_cred.return_value = mock_credential
            
            result = validate_azure_authentication()
            
            assert result["status"] == "configured"
            assert result["environment"] == "azure_hosted"
            assert result["credential_type"] == "managed_identity"
            assert "AZURE_CLIENT_ID" in result["azure_env_indicators"]
            assert "MSI_ENDPOINT" in result["azure_env_indicators"]
    
    def test_validate_azure_authentication_managed_identity_system_assigned(self, monkeypatch):
        """Test validation with system-assigned managed identity"""
        monkeypatch.setenv("IDENTITY_ENDPOINT", "http://localhost")
        monkeypatch.delenv("AZURE_CLIENT_ID", raising=False)
        
        with patch('utils.credential_util.get_azure_credential') as mock_get_cred:
            mock_credential = Mock()
            mock_get_cred.return_value = mock_credential
            
            result = validate_azure_authentication()
            
            assert result["environment"] == "azure_hosted"
            assert "system-assigned" in result["recommendations"][0]
    
    def test_validate_azure_authentication_local_development(self, monkeypatch):
        """Test validation in local development"""
        for key in ["WEBSITE_SITE_NAME", "AZURE_CLIENT_ID", "MSI_ENDPOINT", 
                    "IDENTITY_ENDPOINT", "KUBERNETES_SERVICE_HOST"]:
            monkeypatch.delenv(key, raising=False)
        
        with patch('utils.credential_util.get_azure_credential') as mock_get_cred:
            mock_credential = Mock()
            mock_get_cred.return_value = mock_credential
            
            result = validate_azure_authentication()
            
            assert result["status"] == "configured"
            assert result["environment"] == "local_development"
            assert result["credential_type"] == "cli_credentials"
            assert any("azd auth login" in str(rec) for rec in result["recommendations"])
            assert any("az login" in str(rec) for rec in result["recommendations"])
    
    def test_validate_azure_authentication_error_handling(self, monkeypatch):
        """Test validation error handling"""
        for key in ["WEBSITE_SITE_NAME", "AZURE_CLIENT_ID", "MSI_ENDPOINT"]:
            monkeypatch.delenv(key, raising=False)
        
        with patch('utils.credential_util.get_azure_credential') as mock_get_cred:
            mock_get_cred.side_effect = Exception("Authentication failed")
            
            result = validate_azure_authentication()
            
            assert result["status"] == "error"
            assert "error" in result
            assert "Authentication failed" in result["error"]
            assert "Authentication setup failed" in result["recommendations"][-1]
    
    def test_validate_azure_authentication_container_registry(self, monkeypatch):
        """Test validation in Azure Container Registry environment"""
        monkeypatch.setenv("CONTAINER_REGISTRY_LOGIN", "myregistry")
        monkeypatch.delenv("AZURE_CLIENT_ID", raising=False)
        
        with patch('utils.credential_util.get_azure_credential') as mock_get_cred:
            mock_credential = Mock()
            mock_get_cred.return_value = mock_credential
            
            result = validate_azure_authentication()
            
            # Note: CONTAINER_REGISTRY_LOGIN might not be recognized by all implementations
            assert result["status"] == "configured"
            assert result["credential_instance"] is not None
