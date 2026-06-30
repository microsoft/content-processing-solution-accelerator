# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Global test configuration and fixtures for ContentProcessorAPI tests."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(__file__))

pytest_plugins = ["pytest_mock"]


@pytest.fixture(autouse=True, scope="function")
def mock_azure_credentials_for_helpers(request):
    """Auto-mock Azure credentials for helper tests; skip for credential-util tests."""
    if "test_azure_credential_utils" in str(request.fspath):
        yield
        return

    with (
        patch("app.utils.azure_credential_utils.get_azure_credential") as mock_get_cred,
        patch(
            "app.utils.azure_credential_utils.get_azure_credential_async"
        ) as mock_get_cred_async,
    ):
        mock_credential = MagicMock()
        mock_get_cred.return_value = mock_credential
        mock_get_cred_async.return_value = mock_credential

        yield mock_credential
