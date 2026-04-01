# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Dynamically load Python modules stored in Azure Blob Storage.

Used by the map handler to fetch schema classes at runtime from a
configurable blob container.
"""

import importlib.util
import sys

from azure.storage.blob import BlobServiceClient

from libs.utils.azure_credential_utils import get_azure_credential


def load_schema_from_blob(
    account_url: str, container_name: str, blob_name: str, module_name: str
):
    """Download a Python file from blob storage and return a class from it.

    Args:
        account_url: Azure Blob Storage account URL.
        container_name: Container (path) holding the blob.
        blob_name: Blob filename to download.
        module_name: Name of the class to extract from the module.

    Returns:
        The class object loaded from the downloaded script.
    """
    # Download the blob content
    blob_content = _download_blob_content(container_name, blob_name, account_url)

    # Execute the script content
    module = _execute_script(blob_content, module_name)

    loaded_class = getattr(module, module_name)
    return loaded_class


def _download_blob_content(container_name, blob_name, account_url):
    """Download blob content as a UTF-8 string."""
    credential = get_azure_credential()
    blob_service_client = BlobServiceClient(
        account_url=account_url, credential=credential
    )

    blob_client = blob_service_client.get_blob_client(
        container=container_name, blob=blob_name
    )

    blob_content = blob_client.download_blob().readall().decode("utf-8")
    return blob_content


def _execute_script(script_content, module_name):
    """Execute Python source text as a new module and return it."""
    spec = importlib.util.spec_from_loader(module_name, loader=None)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    # Execute the script content in the module's namespace
    exec(script_content, module.__dict__)
    return module
