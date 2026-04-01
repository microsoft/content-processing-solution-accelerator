# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Pydantic models for content-processing queue messages.

These models mirror the queue message schema expected by the
ContentProcessor worker (``src/ContentProcessor``).  They must stay
in sync with ``ContentProcessorAPI/app/routers/models/contentprocessor/model.py``.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field
from sas.cosmosdb.mongo.model import RootEntityBase


class ArtifactType(str, Enum):
    Undefined = "undefined"
    ConvertedContent = "converted_content"
    ExtractedContent = "extracted_content"
    SchemaMappedData = "schema_mapped_data"
    ScoreMergedData = "score_merged_data"
    SourceContent = "source_content"
    SavedContent = "saved_content"


class PipelineStep(str, Enum):
    Transform = "transform"
    Extract = "extract"
    Mapping = "map"
    Evaluating = "evaluate"
    Save = "save"


class ProcessFile(BaseModel):
    process_id: str
    id: str
    name: str
    size: int
    mime_type: str
    artifact_type: ArtifactType
    processed_by: str


class PipelineStatus(BaseModel):
    process_id: str
    schema_id: str
    metadata_id: str
    completed: Optional[bool] = Field(default=False)
    creation_time: datetime
    last_updated_time: Optional[datetime] = Field(default=None)
    steps: list[str] = Field(default_factory=list)
    remaining_steps: Optional[list[str]] = Field(default_factory=list)
    completed_steps: Optional[list[str]] = Field(default_factory=list)


class ContentProcessMessage(BaseModel):
    """Queue message payload for a content-processing job."""

    process_id: str
    files: list[ProcessFile] = Field(default_factory=list)
    pipeline_status: PipelineStatus = Field(default_factory=PipelineStatus)


class ContentProcessRecord(RootEntityBase):
    """Cosmos DB entity for the Processes collection.

    Maps the document structure written by ContentProcessor/API.
    Only the fields we read are declared; extra fields are allowed
    so downstream writes (by the ContentProcessor worker) are preserved.
    """

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    process_id: str = ""
    processed_file_name: Optional[str] = None
    processed_file_mime_type: Optional[str] = None
    processed_time: Optional[str] = None
    imported_time: Optional[datetime] = None
    status: Optional[str] = None
    entity_score: Optional[float] = 0.0
    schema_score: Optional[float] = 0.0
    result: Optional[Any] = None
    confidence: Optional[Any] = None

    def to_cosmos_dict(self) -> Dict[str, Any]:
        """Convert to Cosmos DB document, preserving native datetime objects.

        Overrides the base ``to_cosmos_dict()`` which uses
        ``model_dump(mode="json")`` and converts datetime to ISO strings.
        PyMongo needs native ``datetime`` objects to store them as BSON
        datetime, matching how ContentProcessor writes the same field.
        """
        data = self.model_dump(by_alias=True, exclude_none=False)
        return data
