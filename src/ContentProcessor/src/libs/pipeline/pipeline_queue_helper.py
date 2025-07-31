# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import logging

from azure.core.exceptions import ResourceNotFoundError
from helpers.azure_credential_utils import get_azure_credential
from azure.storage.queue import QueueClient, QueueMessage

from libs.pipeline import pipeline_step_helper
from libs.pipeline.entities.pipeline_data import DataPipeline


def create_queue_client_name(step_name: str) -> str:
    return f"content-pipeline-{step_name}-queue"


def create_dead_letter_queue_client_name(step_name: str) -> str:
    return f"{create_queue_client_name(step_name)}-dead-letter-queue"


def invalidate_queue(queue_client: QueueClient):
    try:
        queue_client.get_queue_properties()
    except ResourceNotFoundError:
        logging.info("Queue not found. Creating a new queue.")
        queue_client.create_queue()


def create_or_get_queue_client(
    queue_name: str, accouont_url: str, credential: get_azure_credential
) -> QueueClient:
    queue_client = QueueClient(
        account_url=accouont_url, queue_name=queue_name, credential=credential
    )
    invalidate_queue(queue_client)
    return queue_client


def delete_queue_message(message: QueueMessage, queue_client: QueueClient):
    queue_client.delete_message(message=message)


def move_to_dead_letter_queue(
    message: QueueMessage,
    dead_letter_queue_client: QueueClient,
    queue_client: QueueClient,
):
    dead_letter_queue_client.send_message(content=message.content)
    delete_queue_message(message=message, queue_client=queue_client)


def has_messages(queue_client: QueueClient) -> bool:
    return queue_client.peek_messages(max_messages=1)


def pass_data_pipeline_to_next_step(
    data_pipeline: DataPipeline, account_url: str, credential: get_azure_credential
):
    next_step_name = pipeline_step_helper.get_next_step_name(
        data_pipeline.pipeline_status, data_pipeline.pipeline_status.active_step
    )
    # If there is no next step, then we are done
    if next_step_name is None:
        return

    _create_queue_client(
        account_url, create_queue_client_name(next_step_name), credential
    ).send_message(data_pipeline.model_dump_json())


def _create_queue_client(
    account_url: str, queue_name: str, credential: get_azure_credential
) -> QueueClient:
    queue_client = QueueClient(
        account_url=account_url, queue_name=queue_name, credential=credential
    )
    invalidate_queue(queue_client)
    return queue_client
