# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Domain models for the claim-processing workflow.

These Pydantic models are persisted as JSON documents in Cosmos DB
(MongoDB API) by ``Claim_Processes`` and flow through every pipeline
stage — document ingestion, summarisation, and gap analysis.

Classes:
    Claim_Steps
        Enum of the high-level workflow stages a claim passes through.
    Content_Process
        Per-document processing result (file name, scores, status).
    Claim_Process
        Root aggregate that tracks the full lifecycle of a single
        claim batch, including its list of ``Content_Process`` entries.
"""

import datetime
from enum import Enum
from typing import Optional

from pydantic import Field
from sas.cosmosdb.mongo.model import EntityBase, RootEntityBase


class Claim_Steps(str, Enum):
    """
    High-level stages in the claim-processing workflow.

    Values:
        PENDING:              Claim is queued but not yet started.
        DOCUMENT_PROCESSING:  Individual documents are being extracted.
        SUMMARIZING:          Documents have been processed; summary is
                              being generated.
        GAP_ANALYSIS:         Summary is complete; gaps are being
                              identified.
        FAILED:               An unrecoverable error occurred.
        COMPLETED:            All stages finished successfully.
    """

    PENDING = "Pending"
    DOCUMENT_PROCESSING = "Processing"
    SUMMARIZING = "Summarizing"
    GAP_ANALYSIS = "GapAnalysis"
    RAI_ANALYSIS = "RAIAnalysis"
    FAILED = "Failed"
    COMPLETED = "Completed"


class Content_Process(EntityBase):
    """
    Per-document result produced by the content-processing stage.

    Each instance represents one file that was submitted as part of a
    claim batch.  The downstream summarisation and gap-analysis steps
    consume the ``entity_score`` and ``schema_score`` to assess document
    quality.

    Attributes:
        process_id:     Links back to the parent ``Claim_Process``.
        file_name:      Original file name (used as a dedup key together
                        with *process_id*).
        mime_type:      MIME type detected during ingestion.
        entity_score:   Quality metric for entity extraction (0.0–1.0).
        schema_score:   Quality metric for schema conformance (0.0–1.0).
        status:         Human-readable processing outcome.
        processed_time: ISO-8601 timestamp of completion.
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
    """
    Root aggregate for a single claim-batch workflow run.

    This document is the authoritative record of progress: the queue
    consumer creates it at the start, each pipeline stage updates
    ``status`` and appends to ``processed_documents``, and the final
    stage writes ``process_summary`` and ``process_gaps``.

    Attributes:
        id:                   Unique batch identifier.
        process_name:         Workflow label (default *First Notice of Loss*).
        schemaset_id:         Schema set used for content extraction.
        metadata_id:          Optional metadata reference.
        processed_documents:  Running list of ``Content_Process`` results.
        status:               Current ``Claim_Steps`` stage.
        process_summary:      Aggregated summary produced by the
                              summarisation stage.
        process_gaps:         Gap-analysis output.
        process_comment:      Free-text comment added by a specialist.
        process_time:         ISO-8601 timestamp of batch creation.
        processed_time:       ISO-8601 timestamp of batch completion.
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
        default_factory=lambda: datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),
    )
    processed_time: str = Field(
        description="Timestamp of when the claim processing was completed", default=""
    )
