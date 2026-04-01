# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Business logic for schema-set CRUD operations (Cosmos DB + Blob Storage)."""

import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.libs.application.application_configuration import AppConfiguration
from app.libs.application.application_context import AppContext
from app.libs.azure.cosmos_db.helper import CosmosMongDBHelper
from app.libs.azure.storage_blob.helper import StorageBlobHelper
from app.routers.models.schmavault.model import Schema, SchemaMetadata, SchemaSet


class SchemaSets(BaseModel):
    """CRUD operations for schema sets, backed by Cosmos DB and Blob Storage."""

    config: AppConfiguration = Field(default=None)
    blobHelper: StorageBlobHelper = Field(default=None)
    mongoHelper_schemasets: CosmosMongDBHelper = Field(default=None)
    mongoHelper_schemas: CosmosMongDBHelper = Field(default=None)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, app_context: AppContext = None):
        super().__init__()
        self.config = app_context.configuration
        self.blobHelper = StorageBlobHelper(
            self.config.app_storage_blob_url,
            f"{self.config.app_cps_configuration}/{self.config.app_cosmos_container_schemaset}",
        )
        self.mongoHelper_schemasets = CosmosMongDBHelper(
            connection_string=self.config.app_cosmos_connstr,
            db_name=self.config.app_cosmos_database,
            container_name=self.config.app_cosmos_container_schemaset,
            indexes=[("Name", 1), ("Id", 1)],
        )

        self.mongoHelper_schemas = CosmosMongDBHelper(
            connection_string=self.config.app_cosmos_connstr,
            db_name=self.config.app_cosmos_database,
            container_name=self.config.app_cosmos_container_schema,
            indexes=[("ClassName", 1), ("Id", 1)],
        )

    def GetAll(self) -> list[SchemaSet]:
        """Return all schema sets, sorted by name."""
        schemasets = self.mongoHelper_schemasets.find_document(
            query={}, sort_fields=[("Name", 1)]
        )
        return [SchemaSet(**schemaset) for schemaset in schemasets]

    def AddNew(self, Name: str, Description: str) -> SchemaSet:
        """Create and persist a new schema set."""
        new_schemaset = SchemaSet(
            Id=str(uuid.uuid4()),
            Name=Name,
            Description=Description,
            Created_On=datetime.datetime.now(datetime.timezone.utc),
            Updated_On=datetime.datetime.now(datetime.timezone.utc),
            Schemas=[],
        )

        self.mongoHelper_schemasets.insert_document(
            new_schemaset.model_dump(mode="json")
        )
        return new_schemaset

    def GetById(self, schemaset_id: str) -> SchemaSet | None:
        """Return a schema set by ID, or ``None`` if not found."""
        schemaset_obj = self.mongoHelper_schemasets.find_document(
            query={"Id": schemaset_id}
        )

        if not schemaset_obj:
            return None

        return SchemaSet(**schemaset_obj[0])

    def DeleteById(self, schemaset_id: str) -> bool:
        """Delete a schema set by ID. Return ``True`` if deleted."""
        result = self.mongoHelper_schemasets.delete_document(
            schemaset_id, field_name="Id"
        )
        return result.deleted_count > 0

    def AddSchemaToSet(self, schemaset_id: str, schema_id: str) -> SchemaSet:
        """Append a registered schema to the given schema set."""
        schemaset_docs = self.mongoHelper_schemasets.find_document(
            query={"Id": schemaset_id}
        )
        if not schemaset_docs:
            raise Exception("Schema Set not found")

        schemaset = SchemaSet(**schemaset_docs[0])

        schema_docs = self.mongoHelper_schemas.find_document(query={"Id": schema_id})
        if not schema_docs:
            raise Exception("Schema not found")

        schema_object = Schema(**schema_docs[0])
        schemaset.Schemas.append(
            SchemaMetadata(
                Id=str(uuid.uuid4()),
                SchemaId=schema_object.Id,
                Description=schema_object.Description,
            )
        )

        schemaset.Updated_On = datetime.datetime.now(datetime.timezone.utc)
        self.mongoHelper_schemasets.update_document_by_query(
            query={"Id": schemaset_id},
            update={
                "Schemas": [sm.model_dump(mode="json") for sm in schemaset.Schemas],
                "Updated_On": schemaset.Updated_On,
            },
        )
        return schemaset

    def RemoveSchemaFromSet(self, schemaset_id: str, schema_id: str) -> SchemaSet:
        """Remove a schema from the schema set by *schema_id*."""
        schemaset_docs = self.mongoHelper_schemasets.find_document(
            query={"Id": schemaset_id}
        )
        if not schemaset_docs:
            raise Exception("Schema Set not found")

        schemaset = SchemaSet(**schemaset_docs[0])

        updated_schemas = [sm for sm in schemaset.Schemas if sm.SchemaId != schema_id]
        schemaset.Schemas = updated_schemas
        schemaset.Updated_On = datetime.datetime.now(datetime.timezone.utc)

        self.mongoHelper_schemasets.update_document_by_query(
            query={"Id": schemaset_id},
            update={
                "Schemas": [sm.model_dump(mode="json") for sm in updated_schemas],
                "Updated_On": schemaset.Updated_On,
            },
        )
        return schemaset

    def GetAllSchemasInSet(self, schemaset_id: str) -> list[Schema]:
        """Return the full ``Schema`` objects belonging to the given set."""
        schemaset_docs = self.mongoHelper_schemasets.find_document(
            query={"Id": schemaset_id}
        )
        if not schemaset_docs:
            raise Exception("Schema Set not found")

        schemaset = SchemaSet(**schemaset_docs[0])

        schema_list = []
        for schema_meta in schemaset.Schemas:
            schema_docs = self.mongoHelper_schemas.find_document(
                query={"Id": schema_meta.SchemaId}
            )
            if schema_docs:
                schema_list.append(Schema(**schema_docs[0]))
        return schema_list
