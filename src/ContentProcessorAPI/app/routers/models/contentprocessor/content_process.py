# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import datetime
import json
from typing import Any, List, Optional

from pydantic import BaseModel, SkipValidation

from app.libs.cosmos_db.helper import CosmosMongDBHelper
from app.libs.storage_blob.helper import StorageBlobHelper
from app.routers.models.schmavault.model import Schema


class ExtractionComparisonItem(BaseModel):
    Field: Optional[str]
    Extracted: Optional[Any]
    Confidence: Optional[str]
    IsAboveThreshold: Optional[bool]

    def to_dict(self) -> dict:
        return self.model_dump()

    def to_json(self) -> str:
        return self.model_dump_json(indent=4)


class ExtractionComparisonData(BaseModel):
    items: List[ExtractionComparisonItem]

    def to_dict(self) -> dict:
        return self.model_dump()

    def to_json(self) -> str:
        return self.model_dump_json(indent=4)


class Step_Outputs(BaseModel):
    step_name: str
    processed_time: Optional[str] = None
    step_result: SkipValidation[Any]

    class Config:
        arbitrary_types_allowed = True


class PaginatedResponse(BaseModel):
    total_count: int
    total_pages: int
    current_page: int
    page_size: int
    items: List["ContentProcess"]


class ContentProcess(BaseModel):
    """this model is used for Cosmos DB Entity"""

    process_id: str
    processed_file_name: Optional[str] = None
    processed_file_mime_type: Optional[str] = None
    processed_time: Optional[str] = None
    imported_time: datetime.datetime = datetime.datetime.now(datetime.UTC)
    last_modified_time: datetime.datetime = datetime.datetime.now(datetime.UTC)
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

    process_output: list[Step_Outputs] = []
    extracted_comparison_data: Optional[ExtractionComparisonData] = None

    comment: Optional[str] = None

    def update_process_status_to_cosmos(
        self,
        connection_string: str,
        database_name: str,
        collection_name: str,
    ):
        """
        Update the status of the process in Cosmos DB.
        """
        # Check if the process_id is already in the database
        mongo_helper = CosmosMongDBHelper(
            connection_string=connection_string,
            db_name=database_name,
            container_name=collection_name,
            indexes=[("process_id", 1)],
        )

        # Check if the process_id already exists in the database
        existing_process = mongo_helper.find_document(
            query={"process_id": self.process_id}
        )
        if existing_process:
            # Update the existing document
            mongo_helper.update_document_by_query(
                {"process_id": self.process_id},
                {
                    "status": self.status,
                    "processed_file_name": self.processed_file_name,
                },
            )
        else:
            # Insert a new document
            mongo_helper.insert_document(self.model_dump())

    def update_status_to_cosmos(
        self, connection_string: str, database_name: str, collection_name: str
    ):
        """
        Update the status of the process in Cosmos DB.
        """
        # Check if the process_id is already in the database
        mongo_helper = CosmosMongDBHelper(
            connection_string=connection_string,
            db_name=database_name,
            container_name=collection_name,
            indexes=[("process_id", 1)],
        )

        # Check if the process_id already exists in the database
        existing_process = mongo_helper.find_document({"process_id": self.process_id})
        if existing_process:
            # Update the existing document
            mongo_helper.update_document_by_query(
                {"process_id": self.process_id}, self.model_dump()
            )
        else:
            # Insert a new document
            mongo_helper.insert_document(self.model_dump())

    def get_status_from_blob(
        self,
        connection_string: str,
        container_name: str,
        blob_name: str,
    ) -> list[Step_Outputs]:
        """Get ths step outputs from blob storage then return Step_Outputs list"""
        blob_helper = StorageBlobHelper(
            account_url=connection_string, container_name=container_name
        )

        # Download the blob content
        try:
            blob_steps_list = blob_helper.download_blob(blob_name=blob_name).decode(
                "utf-8"
            )
        except Exception:
            # blob not found. return empty list
            return []

        blob_content_list = json.loads(blob_steps_list)  # load string to dict

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
        """
        Get the status of the process from Cosmos DB.
        """
        # Check if the process_id is already in the database
        mongo_helper = CosmosMongDBHelper(
            connection_string=connection_string,
            db_name=database_name,
            container_name=collection_name,
            indexes=[("process_id", 1)],
        )

        # Check if the process_id already exists in the database
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
        """
        Delete the processed file from Cosmos DB & Storage account.
        """
        mongo_helper = CosmosMongDBHelper(
            connection_string=connection_string,
            db_name=database_name,
            container_name=collection_name,
            indexes=[("process_id", 1)],
        )

        blob_helper = StorageBlobHelper(
            account_url=storage_connection_string, container_name=container_name
        )

        # Check if the process_id already exists in the database
        existing_process = mongo_helper.find_document(
            query={"process_id": self.process_id}
        )

        blob_helper.delete_folder(folder_name=self.process_id)

        if existing_process:
            mongo_helper.delete_document(item_id=self.process_id, field_name="process_id")
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
        # Update the process result in Cosmos DB
        mongo_helper = CosmosMongDBHelper(
            connection_string=connection_string,
            db_name=database_name,
            container_name=collection_name,
            indexes=[("process_id", 1)],
        )
        # Check if the process_id already exists in the database
        existing_process = mongo_helper.find_document(
            query={"process_id": self.process_id}
        )
        if existing_process:
            # Update the existing document
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
        # Update the process result in Cosmos DB
        mongo_helper = CosmosMongDBHelper(
            connection_string=connection_string,
            db_name=database_name,
            container_name=collection_name,
            indexes=[("process_id", 1)],
        )
        # Check if the process_id already exists in the database
        existing_process = mongo_helper.find_document(
            query={"process_id": self.process_id}
        )
        if existing_process:
            # Update the existing document
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
        """
        Get all processes from Cosmos DB.
        """
        # Check if the process_id is already in the database
        mongo_helper = CosmosMongDBHelper(
            connection_string=connection_string,
            db_name=database_name,
            container_name=collection_name,
            indexes=[("process_id", 1), ("imported_time", -1)],
        )

        total_count = mongo_helper.count_documents()
        total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1

        # Check if the process_id already exists in the database
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
            # Return an empty list if no processes are found
            return PaginatedResponse(
                total_count=0, total_pages=0, current_page=0, page_size=0, items=[]
            )

    def get_file_bytes_from_blob(
        self,
        connection_string: str,
        container_name: str,
        blob_name: str,
    ) -> bytes:
        """
        Get the files from blob storage.
        """
        blob_helper = StorageBlobHelper(
            account_url=connection_string, container_name=container_name
        )

        return blob_helper.download_blob(blob_name=blob_name)

    class Config:
        arbitrary_types_allowed = True
