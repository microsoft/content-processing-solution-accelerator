# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import json
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class ContentProcessorRequest(BaseModel):
    Metadata_Id: str
    Schema_Id: str

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return cls(**json.loads(value))
        return value


class ArtifactType(str, Enum):
    Undefined = "undefined"
    ConvertedContent = "converted_content"
    ExtractedContent = "extracted_content"
    SchemaMappedData = "schema_mapped_data"
    ScoreMergedData = "score_merged_data"
    SourceContent = "source_content"
    SavedContent = "saved_content"


# Should be synced with App Configuration APP_PROCESS_STEPS
class Steps(str, Enum):
    Transform = "transform"
    Extract = "extract"
    Mapping = "map"
    Evaluating = "evaluate"
    Save = "save"


class ContentProcessorResponse(BaseModel):
    Process_Id: str
    Metadata_Id: str


class ProcessFile(BaseModel):
    process_id: str
    id: str
    name: str
    size: int
    mime_type: str
    artifact_type: ArtifactType
    processed_by: str


class Paging(BaseModel):
    page_number: int = Field(default=0, gt=0)
    page_size: int = Field(default=0, gt=0)


class ContentResultUpdate(BaseModel):
    process_id: str
    modified_result: dict


class ContentResultDelete(BaseModel):
    process_id: str
    status: str
    message: str


class ContentCommentUpdate(BaseModel):
    process_id: str
    comment: str


class Status(BaseModel):
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
    process_id: str
    files: list[ProcessFile] = Field(default_factory=list)
    pipeline_status: Status = Field(default_factory=Status)
