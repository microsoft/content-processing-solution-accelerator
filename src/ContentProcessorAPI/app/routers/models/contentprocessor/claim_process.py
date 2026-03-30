# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Domain models for claim-process workflow state and pagination."""

import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field
from sas.cosmosdb.mongo.model import EntityBase, RootEntityBase


class Claim_Steps(str, Enum):
    """Lifecycle states for a claim workflow.

    Members:
        PENDING: Claim is waiting to be picked up.
        DOCUMENT_PROCESSING: Documents are being ingested and extracted.
        SUMMARIZING: A summary of the claim is being generated.
        GAP_ANALYSIS: Missing information is being identified.
        RAI_ANALYSIS: Responsible AI analysis is being performed.
        FAILED: Processing encountered an unrecoverable error.
        COMPLETED: All workflow steps finished successfully.
    """

    PENDING = "Pending"
    DOCUMENT_PROCESSING = "Processing"
    SUMMARIZING = "Summarizing"
    GAP_ANALYSIS = "GapAnalysis"
    RAI_ANALYSIS = "RAIAnalysis"
    FAILED = "Failed"
    COMPLETED = "Completed"


class Content_Process(EntityBase):
    """Content-process record with per-document extraction metadata.

    Attributes:
        process_id: Unique identifier for the content-processing step.
        file_name: Original filename of the processed document.
        mime_type: Detected MIME type of the document.
        entity_score: Quality score for entity extraction.
        schema_score: Quality score for schema mapping.
        status: Current pipeline status for this document.
        processed_time: ISO timestamp of processing completion.
    """

    process_id: str = Field(
        description="Unique identifier for the content processing step"
    )
    file_name: str = Field(description="Name of the processed content file")
    mime_type: Optional[str] = Field(
        description="MIME type of the processed content file", default=None
    )
    entity_score: float = Field(
        description="Score indicating the quality of entity extraction from the content",
        default=0.0,
    )
    schema_score: float = Field(
        description="Score indicating the quality of schema matching for the content",
        default=0.0,
    )
    status: Optional[str] = Field(
        description="Indicates the current status in the content processing pipeline",
        default=None,
    )
    processed_time: str = Field(
        description="Timestamp of when the content processing was completed", default=""
    )


class Claim_Process(RootEntityBase):
    """Claim-process aggregate recording workflow state and processed documents.

    Attributes:
        id: Unique identifier for the claim batch processing.
        process_name: Human-readable name for this workflow.
        schemaset_id: Schema-set used during document extraction.
        metadata_id: Optional metadata reference for the claim.
        processed_documents: Documents processed within this claim.
        status: Current lifecycle step of the claim workflow.
        process_summary: Generated summary of the entire claim.
        process_gaps: Identified information gaps in the claim.
        process_comment: Specialist-supplied comments.
        process_time: Timestamp when processing started.
        processed_time: Timestamp when processing completed.
    """

    id: str = Field(description="Unique identifier for the claim batch processing")
    process_name: str = Field(
        description="Name of the claim processing workflow",
        default="First Notice of Loss",
    )
    schemaset_id: str = Field(
        description="Unique identifier for the schemaset used in processing"
    )
    metadata_id: Optional[str] = Field(
        description="Unique identifier for the metadata associated with the claim",
        default=None,
    )
    processed_documents: list[Content_Process] = Field(
        description="List of processed document information", default_factory=lambda: []
    )
    status: Claim_Steps = Field(
        description="Indicates the current step in the processing workflow",
        default=Claim_Steps.DOCUMENT_PROCESSING,
    )
    process_summary: str = Field(
        description="Summary of the entire claim processing", default=""
    )
    process_gaps: str = Field(
        description="Identified gaps in the claim processing", default=""
    )
    process_comment: str = Field(
        description="Additional comments regarding the claim processing by specialists",
        default="",
    )
    process_time: str = Field(
        description="Timestamp of when the claim processing started",
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ"
        ),
    )
    processed_time: str = Field(
        description="Timestamp of when the claim processing was completed", default=""
    )


class PaginatedClaimProcessResponse(BaseModel):
    """Paginated response wrapper for Claim_Process records.

    Attributes:
        total_count: Total number of matching records.
        total_pages: Total number of pages.
        current_page: Current 1-based page number.
        page_size: Number of items per page.
        items: Claim-process records on the current page.
    """

    total_count: int
    total_pages: int
    current_page: int
    page_size: int
    items: list[Claim_Process]
