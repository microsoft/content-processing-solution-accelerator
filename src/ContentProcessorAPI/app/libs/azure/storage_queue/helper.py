# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Helper for sending messages to Azure Storage Queues.

Used by the content-processing and claim routers to enqueue work items
(e.g. extraction requests) that downstream pipeline workers consume.
"""

import logging

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.queue import QueueClient
from pydantic import BaseModel

from app.utils.azure_credential_utils import get_azure_credential


class StorageQueueHelper:
    """Send JSON messages to a single Azure Storage Queue.

    Responsibilities:
        1. Authenticate via DefaultAzureCredential.
        2. Auto-create the queue if it does not exist.
        3. Serialize Pydantic models and enqueue them.

    Attributes:
        queue_client: Authenticated QueueClient for the target queue.
    """

    def __init__(self, account_url, queue_name):
        """Create a helper for *queue_name* on *account_url*.

        Args:
            account_url: Azure Queue Storage account URL.
            queue_name: Name of the target queue.
        """
        credential = get_azure_credential()
        self.queue_client = self.create_or_get_queue_client(
            queue_name=queue_name, accouont_url=account_url, credential=credential
        )

    def drop_message(self, message_object: BaseModel):
        """Serialize *message_object* to JSON and send it to the queue."""
        self.queue_client.send_message(content=message_object.model_dump_json())

    def _invalidate_queue(self, queue_client: QueueClient):
        """Create the queue if it does not already exist."""
        try:
            queue_client.get_queue_properties()
        except ResourceNotFoundError:
            logging.info("Queue not found. Creating a new queue.")
            queue_client.create_queue()

    def create_or_get_queue_client(
        self, queue_name: str, accouont_url: str, credential: get_azure_credential
    ) -> QueueClient:
        """Return a QueueClient for *queue_name*, creating the queue if needed."""
        queue_client = QueueClient(
            account_url=accouont_url, queue_name=queue_name, credential=credential
        )
        self._invalidate_queue(queue_client)
        return queue_client
