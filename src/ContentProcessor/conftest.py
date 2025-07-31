"""
Global test configuration and fixtures for ContentProcessor tests.
"""
import sys
import os
import pytest
from unittest.mock import patch, MagicMock

# Add src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

pytest_plugins = ["pytest_mock"]


@pytest.fixture(autouse=True, scope="function")
def mock_azure_credentials_for_helpers(request):
    """
    Mock Azure credentials for azure_helper classes only.
    Skip this for credential utility tests that need to test the actual logic.
    """
    # Skip mocking for credential utility tests
    if "test_azure_credential_utils" in str(request.fspath):
        yield
        return

    with patch("helpers.azure_credential_utils.get_azure_credential") as mock_get_cred, \
         patch("helpers.azure_credential_utils.get_azure_credential_async") as mock_get_cred_async:

        # Create mock credential objects
        mock_credential = MagicMock()
        mock_get_cred.return_value = mock_credential
        mock_get_cred_async.return_value = mock_credential

        yield mock_credential
