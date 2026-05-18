# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Message processing context passed to pipeline handlers.

Bundles the deserialized ``DataPipeline`` payload with the raw Azure
Storage ``QueueMessage`` so handlers have access to both.
"""

from azure.storage.queue import QueueMessage

from libs.base.application_models import AppModelBase
from libs.pipeline.entities.pipeline_data import DataPipeline


class MessageContext(AppModelBase):
    """
    MessageContext is a class that holds the context of the message being processed.
    It will be passed to handlers to provide context information.

    Attributes:
        data_pipeline (DataPipeline): The DataPipeline object - Canonical process step status bag.
        queue_message (QueueMessage): The QueueMessage object - The message from the queue.
    """

    data_pipeline: DataPipeline
    queue_message: QueueMessage
