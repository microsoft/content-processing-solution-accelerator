# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Request/response models, enums, and pipeline status types for content processing."""

import json
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class ContentProcessorBatchFileAddRequest(BaseModel):
    """Request body for adding a file to an existing claim batch.

    Attributes:
        Claim_Id: Target claim identifier.
        Metadata_Id: Associated metadata identifier.
        Schema_Id: Schema to apply for this file.
    """

    Claim_Id: str
    Metadata_Id: str
    Schema_Id: str

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return cls(**json.loads(value))
        return value


class ContentProcessorRequest(BaseModel):
    """Request body for single-file content processing submission.

    Attributes:
        Metadata_Id: Optional metadata identifier.
        Schema_Id: Optional schema identifier.
    """

    Metadata_Id: Optional[str] = None
    Schema_Id: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return cls(**json.loads(value))
        return value


class ClaimProcessRequest(BaseModel):
    """Request body for triggering claim processing.

    Attributes:
        claim_process_id: Unique identifier of the claim batch to process.
    """

    claim_process_id: str


class BatchStatusRequest(BaseModel):
    """Request body for querying batch status by multiple process IDs.

    Attributes:
        process_ids: Non-empty list of process identifiers to check.
    """

    process_ids: list[str] = Field(default_factory=list, min_length=1)


class ArtifactType(str, Enum):
    """Kind of artifact produced or consumed during content processing.

    Members:
        Undefined: Unclassified artifact.
        ConvertedContent: Output of a format conversion step.
        ExtractedContent: Raw extraction output.
        SchemaMappedData: Extraction mapped to a target schema.
        ScoreMergedData: Merged scored extraction data.
        SourceContent: Original uploaded file.
        SavedContent: Final persisted result.
    """

    Undefined = "undefined"
    ConvertedContent = "converted_content"
    ExtractedContent = "extracted_content"
    SchemaMappedData = "schema_mapped_data"
    ScoreMergedData = "score_merged_data"
    SourceContent = "source_content"
    SavedContent = "saved_content"


class Steps(str, Enum):
    """Pipeline steps (synced with App Configuration ``APP_PROCESS_STEPS``).

    Members:
        Transform: File format conversion.
        Extract: Content extraction via AI.
        Mapping: Schema field mapping.
        Evaluating: Confidence evaluation and scoring.
        Save: Persist final results.
    """

    Transform = "transform"
    Extract = "extract"
    Mapping = "map"
    Evaluating = "evaluate"
    Save = "save"


class ContentProcessorResponse(BaseModel):
    """Response returned after successful file submission.

    Attributes:
        Process_Id: Newly created process identifier.
        Metadata_Id: Metadata identifier echoed from the request.
    """

    Process_Id: str
    Metadata_Id: str


class ProcessFile(BaseModel):
    """Metadata for a single file associated with a process.

    Attributes:
        process_id: Owning process identifier.
        id: Unique file identifier.
        name: Sanitized filename.
        size: File size in bytes.
        mime_type: Detected MIME type.
        artifact_type: Classification of this file in the pipeline.
        processed_by: Agent or user that created this record.
    """

    process_id: str
    id: str
    name: str
    size: int
    mime_type: str
    artifact_type: ArtifactType
    processed_by: str


class Paging(BaseModel):
    """Pagination parameters (1-based page number).

    Attributes:
        page_number: Requested page (must be > 0).
        page_size: Items per page (must be > 0).
    """

    page_number: int = Field(default=0, gt=0)
    page_size: int = Field(default=0, gt=0)


class ContentResultUpdate(BaseModel):
    """Request body for overwriting the processed result.

    Attributes:
        process_id: Target process identifier.
        modified_result: Replacement result dictionary.
    """

    process_id: str
    modified_result: dict


class ContentResultDelete(BaseModel):
    """Response returned after a delete operation.

    Attributes:
        process_id: Deleted process identifier.
        status: ``"Success"`` or ``"Failed"``.
        message: Human-readable status detail.
    """

    process_id: str
    status: str
    message: str


class ContentCommentUpdate(BaseModel):
    """Request body for attaching or updating a user comment.

    Attributes:
        process_id: Target process identifier.
        comment: User-provided comment text.
    """

    process_id: str
    comment: str


class Status(BaseModel):
    """Pipeline execution status tracking completed and remaining steps.

    Attributes:
        process_id: Owning process identifier.
        schema_id: Schema applied to this process.
        metadata_id: Associated metadata identifier.
        completed: Whether all steps have finished.
        creation_time: Timestamp of status creation.
        last_updated_time: Timestamp of last status update.
        steps: Ordered list of all pipeline step names.
        remaining_steps: Steps not yet executed.
        completed_steps: Steps already finished.
    """

    process_id: str
    schema_id: str
    metadata_id: str

    completed: Optional[bool] = Field(default=False)
    creation_time: datetime
    last_updated_time: Optional[datetime] = Field(default=None)
    steps: list[str] = Field(default_factory=list)
    remaining_steps: Optional[list[str]] = Field(default_factory=list)
    completed_steps: Optional[list[str]] = Field(default_factory=list)


class ContentProcess(BaseModel):
    """Queue message payload representing a content-processing job.

    Attributes:
        process_id: Unique process identifier.
        files: Files associated with this job.
        pipeline_status: Current pipeline execution state.
    """

    process_id: str
    files: list[ProcessFile] = Field(default_factory=list)
    pipeline_status: Status = Field(default_factory=Status)
