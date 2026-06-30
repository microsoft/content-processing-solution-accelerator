# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""ContentProcess (aka CosmosContentProcess) domain model with Cosmos DB and Blob Storage persistence."""

import datetime
import json
from typing import Any, List, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SkipValidation,
    field_validator,
    model_validator,
)

from app.libs.azure.cosmos_db.helper import CosmosMongDBHelper
from app.libs.azure.storage_blob.helper import StorageBlobHelper
from app.routers.models.schmavault.model import Schema


class ExtractionComparisonItem(BaseModel):
    """Single row of an extraction-vs-schema comparison report.

    Attributes:
        Field: Schema field name being compared.
        Extracted: Value extracted from the document.
        Confidence: Confidence level label (e.g. ``"High"``, ``"Low"``).
        IsAboveThreshold: Whether the confidence exceeds the acceptance threshold.
    """

    Field: Optional[str]
    Extracted: Optional[Any]
    Confidence: Optional[str]
    IsAboveThreshold: Optional[bool]

    def to_dict(self) -> dict:
        return self.model_dump()

    def to_json(self) -> str:
        return self.model_dump_json(indent=4)


class ExtractionComparisonData(BaseModel):
    """Collection of extraction comparison rows.

    Attributes:
        items: Ordered list of per-field comparison results.
    """

    items: List[ExtractionComparisonItem]

    def to_dict(self) -> dict:
        return self.model_dump()

    def to_json(self) -> str:
        return self.model_dump_json(indent=4)


class Step_Outputs(BaseModel):
    """Output payload from a single pipeline step, stored in blob storage.

    Attributes:
        step_name: Pipeline step that produced this output.
        processed_time: ISO timestamp of when the step completed.
        step_result: Arbitrary result payload (validation skipped).
    """

    step_name: str
    processed_time: Optional[str] = None
    step_result: SkipValidation[Any]

    model_config = ConfigDict(arbitrary_types_allowed=True)


class PaginatedResponse(BaseModel):
    """Paginated response wrapper for ContentProcess records.

    Attributes:
        total_count: Total number of matching records.
        total_pages: Total number of pages.
        current_page: Current 1-based page number.
        page_size: Number of items per page.
        items: Records on the current page.
    """

    total_count: int
    total_pages: int
    current_page: int
    page_size: int
    items: List["ContentProcess"]


class ContentProcess(BaseModel):
    """Content-process aggregate stored in Cosmos DB and Blob Storage.

    Attributes:
        id: Document identifier (defaults to process_id).
        process_id: Unique process identifier.
        processed_file_name: Original uploaded filename.
        processed_file_mime_type: Detected MIME type of the uploaded file.
        processed_time: ISO timestamp of processing completion.
        imported_time: Timestamp when the record was first created.
        last_modified_time: Timestamp of the most recent update.
        last_modified_by: User or agent that last modified the record.
        status: Current processing status string.
        entity_score: Aggregate entity-extraction quality score.
        min_extracted_entity_score: Lowest per-entity extraction score.
        schema_score: Schema-mapping quality score.
        result: Extracted result dictionary.
        confidence: Per-field confidence dictionary.
        target_schema: Schema applied during extraction.
        prompt_tokens: LLM prompt tokens consumed.
        completion_tokens: LLM completion tokens consumed.
        process_output: Per-step output payloads.
        extracted_comparison_data: Extraction-vs-schema comparison rows.
        comment: User-supplied comment.
    """

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    id: Optional[str] = None
    process_id: str
    processed_file_name: Optional[str] = None
    processed_file_mime_type: Optional[str] = None
    processed_time: Optional[str] = None
    imported_time: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )
    last_modified_time: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )
    last_modified_by: Optional[str] = None
    status: Optional[str] = None
    entity_score: Optional[float] = 0.0
    min_extracted_entity_score: Optional[float] = 0.0
    schema_score: Optional[float] = 0.0
    result: Optional[dict] = None
    confidence: Optional[dict] = None
    target_schema: Optional[Schema] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0

    process_output: list[Step_Outputs] = Field(default_factory=list)
    extracted_comparison_data: Optional[ExtractionComparisonData] = None

    comment: Optional[str] = None

    @field_validator("id", mode="before")
    @classmethod
    def _coerce_id_to_str_or_none(cls, value: Any):
        if value is None or isinstance(value, str):
            return value
        return None

    @model_validator(mode="before")
    @classmethod
    def _default_id_from_process_id(cls, data: Any):
        if isinstance(data, dict) and not data.get("id") and data.get("process_id"):
            data["id"] = data["process_id"]
        return data

    @model_validator(mode="after")
    def _coerce_id_from_process_id(self):
        if not isinstance(self.id, str) or not self.id:
            self.id = self.process_id
        return self

    def update_process_status_to_cosmos(
        self,
        connection_string: str,
        database_name: str,
        collection_name: str,
    ):
        """Upsert the current process status into Cosmos DB."""
        mongo_helper = CosmosMongDBHelper(
            connection_string=connection_string,
            db_name=database_name,
            container_name=collection_name,
            indexes=[("process_id", 1)],
        )

        existing_process = mongo_helper.find_document(
            query={"process_id": self.process_id}
        )
        if existing_process:
            mongo_helper.update_document_by_query(
                {"process_id": self.process_id},
                {
                    "status": self.status,
                    "processed_file_name": self.processed_file_name,
                },
            )
        else:
            mongo_helper.insert_document(self.model_dump())

    def update_status_to_cosmos(
        self, connection_string: str, database_name: str, collection_name: str
    ):
        """Upsert the full process document into Cosmos DB."""
        mongo_helper = CosmosMongDBHelper(
            connection_string=connection_string,
            db_name=database_name,
            container_name=collection_name,
            indexes=[("process_id", 1)],
        )

        existing_process = mongo_helper.find_document({"process_id": self.process_id})
        if existing_process:
            mongo_helper.update_document_by_query(
                {"process_id": self.process_id}, self.model_dump()
            )
        else:
            mongo_helper.insert_document(self.model_dump())

    def get_status_from_blob(
        self,
        connection_string: str,
        container_name: str,
        blob_name: str,
    ) -> list[Step_Outputs]:
        """Download step outputs from blob storage and return as a list."""
        blob_helper = StorageBlobHelper(
            account_url=connection_string, container_name=container_name
        )

        try:
            blob_steps_list = blob_helper.download_blob(blob_name=blob_name).decode(
                "utf-8"
            )
        except Exception:
            return []

        blob_content_list = json.loads(blob_steps_list)

        step_outputs_list: List[Step_Outputs] = [
            Step_Outputs.model_validate(item) for item in blob_content_list
        ]

        return step_outputs_list

    def get_status_from_cosmos(
        self,
        connection_string: str,
        database_name: str,
        collection_name: str,
    ):
        """Load the process record from Cosmos DB, or return ``None``."""
        mongo_helper = CosmosMongDBHelper(
            connection_string=connection_string,
            db_name=database_name,
            container_name=collection_name,
            indexes=[("process_id", 1)],
        )

        existing_process = mongo_helper.find_document(
            query={"process_id": self.process_id}
        )
        if existing_process:
            return ContentProcess(**existing_process[0])
        else:
            return None

    def delete_processed_file(
        self,
        connection_string: str,
        database_name: str,
        collection_name: str,
        storage_connection_string: str,
        container_name: str,
    ):
        """Delete the process record from Cosmos DB and its blobs from storage."""
        mongo_helper = CosmosMongDBHelper(
            connection_string=connection_string,
            db_name=database_name,
            container_name=collection_name,
            indexes=[("process_id", 1)],
        )

        blob_helper = StorageBlobHelper(
            account_url=storage_connection_string, container_name=container_name
        )

        existing_process = mongo_helper.find_document(
            query={"process_id": self.process_id}
        )

        blob_helper.delete_folder(folder_name=self.process_id)

        if existing_process:
            mongo_helper.delete_document(
                item_id=self.process_id, field_name="process_id"
            )
            return ContentProcess(**existing_process[0])
        else:
            return None

    def update_process_result(
        self,
        connection_string: str,
        database_name: str,
        collection_name: str,
        process_result: dict,
    ):
        """Overwrite the extracted result dict for this process in Cosmos DB."""
        mongo_helper = CosmosMongDBHelper(
            connection_string=connection_string,
            db_name=database_name,
            container_name=collection_name,
            indexes=[("process_id", 1)],
        )
        existing_process = mongo_helper.find_document(
            query={"process_id": self.process_id}
        )
        if existing_process:
            return mongo_helper.update_document_by_query(
                {"process_id": self.process_id},
                {
                    "result": process_result,
                    "last_modified_time": datetime.datetime.now(datetime.UTC),
                    "last_modified_by": "user",
                },
            )
        else:
            return None

    def update_process_comment(
        self,
        connection_string: str,
        database_name: str,
        collection_name: str,
        comment: str,
    ):
        """Set the user comment for this process in Cosmos DB."""
        mongo_helper = CosmosMongDBHelper(
            connection_string=connection_string,
            db_name=database_name,
            container_name=collection_name,
            indexes=[("process_id", 1)],
        )
        existing_process = mongo_helper.find_document(
            query={"process_id": self.process_id}
        )
        if existing_process:
            return mongo_helper.update_document_by_query(
                {"process_id": self.process_id},
                {
                    "comment": comment,
                    "last_modified_time": datetime.datetime.now(datetime.UTC),
                    "last_modified_by": "user",
                },
            )
        else:
            return None

    @staticmethod
    def get_all_processes_from_cosmos(
        connection_string: str,
        database_name: str,
        collection_name: str,
        page_size: int = 0,
        page_number: int = 0,
    ) -> PaginatedResponse:
        """Return a paginated list of process records from Cosmos DB."""
        mongo_helper = CosmosMongDBHelper(
            connection_string=connection_string,
            db_name=database_name,
            container_name=collection_name,
            indexes=[("process_id", 1), ("imported_time", -1)],
        )

        total_count = mongo_helper.count_documents()
        total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1

        items = mongo_helper.find_document(
            query={},
            sort_fields=[("imported_time", -1)],
            skip=(page_number - 1) * page_size,
            limit=page_size,
            projection=[
                "process_id",
                "processed_file_name",
                "processed_file_mime_type",
                "processed_time",
                "imported_time",
                "last_modified_time",
                "last_modified_by",
                "status",
                "entity_score",
                "min_extracted_entity_score",
                "schema_score",
                "prompt_tokens",
                "completion_tokens",
            ],
        )

        if items:
            return PaginatedResponse(
                total_count=total_count,
                total_pages=total_pages,
                current_page=page_number,
                page_size=page_size,
                items=items,
            )
        else:
            return PaginatedResponse(
                total_count=0, total_pages=0, current_page=0, page_size=0, items=[]
            )

    def get_file_bytes_from_blob(
        self,
        connection_string: str,
        container_name: str,
        blob_name: str,
    ) -> bytes:
        """Download a blob and return its raw bytes."""
        blob_helper = StorageBlobHelper(
            account_url=connection_string, container_name=container_name
        )

        return blob_helper.download_blob(blob_name=blob_name)
