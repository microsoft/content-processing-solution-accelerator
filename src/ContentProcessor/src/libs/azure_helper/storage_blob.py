# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from typing import IO, Union

from helpers.azure_credential_utils import get_azure_credential
from azure.storage.blob import BlobServiceClient


class StorageBlobHelper:
    credential: get_azure_credential = None
    blob_service_client: BlobServiceClient = None

    @staticmethod
    def get(account_url: str, container_name: str = None):
        return StorageBlobHelper(account_url=account_url, container_name=container_name)

    def __init__(self, account_url: str, container_name=None):
        self.credential = get_azure_credential()
        self.blob_service_client = BlobServiceClient(
            account_url=account_url, credential=self.credential
        )
        self.parent_container_name = container_name
        if container_name:
            # if containeer_name is provided, "container_name/folder name" is used, get container_name
            # and create container if not exists
            container_name = container_name.split("/")[0]
            self._invalidate_container(container_name)

    def _invalidate_container(self, container_name: str):
        container_client = self.blob_service_client.get_container_client(container_name)
        if not container_client.exists():
            container_client.create_container()

    def _get_container_client(self, container_name=None):
        if container_name:
            full_container_name = (
                f"{self.parent_container_name}/{container_name}"
                if self.parent_container_name
                else container_name
            )
        elif self.parent_container_name is not None and container_name is None:
            full_container_name = self.parent_container_name
        else:
            raise ValueError(
                "Container name must be provided either during initialization or as a function argument."
            )

        container_client = self.blob_service_client.get_container_client(
            full_container_name
        )

        return container_client

    def upload_file(self, container_name: str, blob_name: str, file_path: str):
        blob_client = self._get_container_client(container_name).get_blob_client(
            blob_name
        )

        with open(file_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)

    def upload_stream(self, container_name: str, blob_name: str, stream: IO):
        blob_client = self._get_container_client(container_name).get_blob_client(
            blob_name
        )

        blob_client.upload_blob(stream, overwrite=True)

    def upload_text(self, container_name: str, blob_name: str, text: str):
        blob_client = self._get_container_client(container_name).get_blob_client(
            blob_name
        )
        blob_client.upload_blob(text, overwrite=True)

    def download_file(self, container_name: str, blob_name: str, download_path: str):
        blob_client = self._get_container_client(container_name).get_blob_client(
            blob_name
        )
        with open(download_path, "wb") as download_file:
            download_file.write(blob_client.download_blob().readall())

    def download_stream(self, container_name: str, blob_name: str) -> bytes:
        blob_client = self._get_container_client(container_name).get_blob_client(
            blob_name
        )
        stream = blob_client.download_blob().readall()
        return stream

    def download_text(self, container_name: str, blob_name: str) -> str:
        blob_client = self._get_container_client(container_name).get_blob_client(
            blob_name
        )
        text = blob_client.download_blob().content_as_text()
        return text

    def delete_blob(self, container_name: str, blob_name: str):
        blob_client = self._get_container_client(container_name).get_blob_client(
            blob_name
        )
        blob_client.delete_blob()

    def update_blob(
        self, container_name: str, blob_name: str, data: Union[str, IO, bytes]
    ):
        self.upload_blob(container_name, blob_name, data)

    def upload_blob(
        self, container_name: str, blob_name: str, data: Union[str, IO, bytes]
    ):
        blob_client = self._get_container_client(container_name).get_blob_client(
            blob_name
        )
        if isinstance(data, str):
            blob_client.upload_blob(data, overwrite=True)
        elif isinstance(data, bytes):
            blob_client.upload_blob(data, overwrite=True)
        elif hasattr(data, "read"):
            blob_client.upload_blob(data, overwrite=True)
        else:
            raise ValueError("Unsupported data type for upload")
