# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Business logic for individual schema registration, update, and deletion."""

from fastapi import UploadFile
from pydantic import BaseModel, ConfigDict, Field

from app.libs.application.application_configuration import (
    AppConfiguration,
)
from app.libs.application.application_context import AppContext
from app.libs.azure.cosmos_db.helper import CosmosMongDBHelper
from app.libs.azure.storage_blob.helper import StorageBlobHelper
from app.routers.models.schmavault.model import Schema


class Schemas(BaseModel):
    """CRUD operations for individual schemas, backed by Cosmos DB and Blob Storage."""

    config: AppConfiguration = Field(default=None)
    blobHelper: StorageBlobHelper = Field(default=None)
    mongoHelper: CosmosMongDBHelper = Field(default=None)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, app_context: AppContext = None):
        super().__init__()
        self.config = app_context.configuration
        self.blobHelper = StorageBlobHelper(
            self.config.app_storage_blob_url,
            f"{self.config.app_cps_configuration}/{self.config.app_cosmos_container_schema}",
        )
        self.mongoHelper = CosmosMongDBHelper(
            connection_string=self.config.app_cosmos_connstr,
            db_name=self.config.app_cosmos_database,
            container_name=self.config.app_cosmos_container_schema,
            indexes=[("ClassName", 1), ("Id", 1)],
        )

    def GetAll(self) -> list[Schema]:
        """Return all registered schemas, sorted by class name."""
        schemas = self.mongoHelper.find_document(query={}, sort_fields=["ClassName"])
        return [Schema(**schema) for schema in schemas]

    def GetFile(self, schema_id: str):
        """Download the schema `.py` file and return it with content metadata."""
        schema_obj = self.mongoHelper.find_document(query={"Id": schema_id})

        if not schema_obj:
            raise Exception("Schema not found")

        schema_obj = Schema(**schema_obj[0])

        return {
            "File": self.blobHelper.download_blob(schema_obj.FileName, schema_obj.Id),
            "ContentType": schema_obj.ContentType,
            "FileName": schema_obj.FileName,
        }

    def Add(self, file: UploadFile, schema: Schema) -> Schema:
        """Upload a schema file to blob storage and insert its metadata."""
        result = self.blobHelper.upload_blob(schema.FileName, file.file, schema.Id)

        schema.Created_On = result["date"]

        self.mongoHelper.insert_document(schema.model_dump(mode="json"))
        return schema

    def Update(
        self,
        file: UploadFile,
        schema_id: str,
        class_name: str,
        storage_format: str = "json",
    ) -> Schema:
        """Replace the schema file in blob storage and update Cosmos metadata."""
        schemas = self.mongoHelper.find_document(query={"Id": schema_id})
        if not schemas:
            raise Exception("Schema not found")

        schema_object = Schema(**schemas[0])
        result = self.blobHelper.replace_blob(
            schema_object.FileName, file.file, schema_id
        )

        schema_object.ClassName = class_name
        schema_object.ContentType = "application/json"
        schema_object.Format = storage_format
        schema_object.Updated_On = result["date"]

        self.mongoHelper.update_document(
            schema_object.Id,
            schema_object.model_dump(mode="json"),
        )
        return schema_object

    def Delete(self, schema_id: str) -> Schema:
        """Delete a schema: remove the Cosmos doc and the blob."""
        schemas = self.mongoHelper.find_document(query={"Id": schema_id})

        if not schemas:
            raise Exception("Schema not found")

        schema_object = Schema(**schemas[0])

        self.mongoHelper.delete_document(schema_id)

        self.blobHelper.delete_blob_and_cleanup(
            schema_object.FileName, schema_object.Id
        )

        return schema_object
