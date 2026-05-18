# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Claim and claim-item domain models with Cosmos DB persistence."""

import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.libs.azure.cosmos_db.helper import CosmosMongDBHelper


class ClaimItem(BaseModel):
    """A single document/file item within a claim.

    Attributes:
        claim_id: Parent claim identifier.
        file_name: Original filename of the uploaded document.
        size: File size in bytes.
        schema_id: Schema applied to this document.
        metadata_id: Reference to associated metadata.
        mime_type: Detected MIME type.
        id: Optional unique item identifier.
    """

    claim_id: str
    file_name: Optional[str] = None
    size: Optional[int] = None
    schema_id: str
    metadata_id: str
    mime_type: Optional[str] = None
    id: Optional[str] = None


class ClaimCreateRequest(BaseModel):
    """Request body for creating a new claim container.

    Attributes:
        schema_collection_id: Schema-set identifier to associate with the new claim.
    """

    schema_collection_id: str


class ClaimProcess(BaseModel):
    """Aggregate root for a claim, containing its items and persistence helpers.

    Attributes:
        claim_id: Unique claim identifier.
        schema_collection_id: Associated schema-set identifier.
        created_time: UTC timestamp when the claim was created.
        last_modified_time: UTC timestamp of the most recent update.
        items: Document items belonging to this claim.
    """

    claim_id: str
    schema_collection_id: str

    created_time: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    last_modified_time: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    items: list[ClaimItem] = Field(default_factory=list)

    def save(
        self,
        *,
        connection_string: str,
        database_name: str,
        collection_name: str,
    ):
        """Upsert this claim process into Cosmos DB."""
        mongo_helper = CosmosMongDBHelper(
            connection_string=connection_string,
            db_name=database_name,
            container_name=collection_name,
            indexes=[("claim_id", 1), ("created_time", -1)],
        )

        existing = mongo_helper.find_document(query={"claim_id": self.claim_id})
        self.last_modified_time = datetime.datetime.now(datetime.timezone.utc)
        if existing:
            mongo_helper.update_document_by_query(
                {"claim_id": self.claim_id}, self.model_dump()
            )
        else:
            mongo_helper.insert_document(self.model_dump())

    @staticmethod
    def get(
        *,
        claim_id: str,
        connection_string: str,
        database_name: str,
        collection_name: str,
    ) -> Optional["ClaimProcess"]:
        """Load a claim process from Cosmos DB by *claim_id*, or return ``None``."""
        mongo_helper = CosmosMongDBHelper(
            connection_string=connection_string,
            db_name=database_name,
            container_name=collection_name,
            indexes=[("claim_id", 1), ("created_time", -1)],
        )

        items = mongo_helper.find_document(query={"claim_id": claim_id})
        if not items:
            return None
        return ClaimProcess(**items[0])
