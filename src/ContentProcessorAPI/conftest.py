"""
Global test configuration and fixtures for ContentProcessorAPI tests.
"""
import sys
import os
import pytest
from unittest.mock import patch, MagicMock

# Add current directory to Python path for imports
sys.path.insert(0, os.path.dirname(__file__))

pytest_plugins = ["pytest_mock"]


@pytest.fixture(autouse=True, scope="session")
def mock_azure_services():
    """
    Mock all Azure services and credentials to prevent real authentication
    and network calls during testing.
    """
    with patch("azure.identity.DefaultAzureCredential") as mock_default, \
         patch("azure.identity.ManagedIdentityCredential") as mock_managed, \
         patch("helpers.azure_credential_utils.get_azure_credential") as mock_get_cred, \
         patch("helpers.azure_credential_utils.get_azure_credential_async") as mock_get_cred_async:
        
        # Create mock credential objects
        mock_credential = MagicMock()
        mock_default.return_value = mock_credential
        mock_managed.return_value = mock_credential
        mock_get_cred.return_value = mock_credential
        mock_get_cred_async.return_value = mock_credential
        
        yield {
            "credential": mock_credential,
            "default": mock_default,
            "managed": mock_managed,
            "get_credential": mock_get_cred,
            "get_credential_async": mock_get_cred_async
        }
