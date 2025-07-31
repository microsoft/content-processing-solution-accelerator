# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import importlib.util
import sys

from helpers.azure_credential_utils import get_azure_credential
from azure.storage.blob import BlobServiceClient


def load_schema_from_blob(
    account_url: str, container_name: str, blob_name: str, module_name: str
):
    """
    Load the schema from a blob in Azure Storage.
    """
    # Download the blob content
    blob_content = _download_blob_content(container_name, blob_name, account_url)

    # Execute the script content
    module_name = module_name
    module = _execute_script(blob_content, module_name)

    loaded_class = getattr(module, module_name)
    return loaded_class


def _download_blob_content(container_name, blob_name, account_url):
    # Create the BlobServiceClient object which will be used to create a container client
    credential = get_azure_credential()
    blob_service_client = BlobServiceClient(
        account_url=account_url, credential=credential
    )

    # Create a blob client using the local file name as the name for the blob
    blob_client = blob_service_client.get_blob_client(
        container=container_name, blob=blob_name
    )

    print(f"\nDownloading blob content from \n\t{blob_name}")

    # Download the blob content as a string
    blob_content = blob_client.download_blob().readall().decode("utf-8")
    return blob_content


def _execute_script(script_content, module_name):
    # Create a new module
    spec = importlib.util.spec_from_loader(module_name, loader=None)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    # Execute the script content in the module's namespace
    exec(script_content, module.__dict__)
    return module
