# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Manifest models deserialised from the ``manifest.json`` blob.

When a new claim batch is submitted, the front-end writes a
``manifest.json`` file into the process-batch storage container.
``DocumentProcessExecutor`` downloads and parses it into a
``ClaimProcess`` instance to discover the files to process and
their associated schema / metadata IDs.
"""

import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ClaimItem(BaseModel):
    """Single file entry within a claim-batch manifest.

    Attributes:
        claim_id:   Parent claim batch identifier.
        file_name:  Blob name of the file to process.
        size:       File size in bytes (optional).
        schema_id:  Schema to apply during content extraction.
        metadata_id: Metadata record linked to this file.
        mime_type:  Detected MIME type (optional).
        id:         Optional unique item identifier.
    """

    claim_id: str
    file_name: Optional[str] = None
    size: Optional[int] = None
    schema_id: str
    metadata_id: str
    mime_type: Optional[str] = None
    id: Optional[str] = None


class ClaimProcess(BaseModel):
    """Top-level manifest for a claim-batch submission.

    Deserialised from ``{claim_id}/manifest.json`` in the process-batch
    blob container.  Carries the schema-collection reference and the
    list of ``ClaimItem`` files to process.

    Attributes:
        claim_id:              Unique batch identifier.
        schema_collection_id:  Schema set governing extraction.
        metadata_id:           Optional metadata reference.
        created_time:          UTC timestamp of batch creation.
        last_modified_time:    UTC timestamp of last update.
        items:                 Files to process in this batch.
    """

    claim_id: str
    schema_collection_id: str
    metadata_id: Optional[str] = None

    created_time: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    last_modified_time: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    items: list[ClaimItem] = Field(default_factory=list)
