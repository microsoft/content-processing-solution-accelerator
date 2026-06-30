# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Test configuration and shared fixtures for all ContentProcessor tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True, scope="function")
def mock_azure_credentials_for_helpers(request):
    """Mock Azure credentials for azure_helper classes only.

    Credential utility tests that exercise the real factory logic are
    excluded so they can patch individual credential classes themselves.
    """
    if "test_azure_credential_utils" in str(request.fspath):
        yield
        return

    with (
        patch(
            "libs.utils.azure_credential_utils.get_azure_credential"
        ) as mock_get_cred,
        patch(
            "libs.utils.azure_credential_utils.get_async_azure_credential"
        ) as mock_get_cred_async,
    ):
        mock_credential = MagicMock()
        mock_get_cred.return_value = mock_credential
        mock_get_cred_async.return_value = mock_credential
        yield mock_credential
