# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import logging

from azure.core.exceptions import ResourceNotFoundError
from helpers.azure_credential_utils import get_azure_credential
from azure.storage.queue import QueueClient
from pydantic import BaseModel


class StorageQueueHelper:
    def __init__(self, account_url, queue_name):
        credential = get_azure_credential()
        self.queue_client = self.create_or_get_queue_client(
            queue_name=queue_name, accouont_url=account_url, credential=credential
        )

    def drop_message(self, message_object: BaseModel):
        self.queue_client.send_message(content=message_object.model_dump_json())

    def _invalidate_queue(self, queue_client: QueueClient):
        try:
            queue_client.get_queue_properties()
        except ResourceNotFoundError:
            logging.info("Queue not found. Creating a new queue.")
            queue_client.create_queue()

    def create_or_get_queue_client(
        self, queue_name: str, accouont_url: str, credential: get_azure_credential
    ) -> QueueClient:
        queue_client = QueueClient(
            account_url=accouont_url, queue_name=queue_name, credential=credential
        )
        self._invalidate_queue(queue_client)
        return queue_client
