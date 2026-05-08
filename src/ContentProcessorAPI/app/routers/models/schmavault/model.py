# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Schema-vault domain models: schemas, schema sets, and related request/response types."""

import datetime
import json
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Schema(BaseModel):
    """Registered schema record stored in Cosmos DB.

    Attributes:
        Id: Unique schema identifier.
        ClassName: Class name of the schema (the JSON Schema ``title``
            field, or a sanitised fallback derived from the filename).
        Description: Human-readable description.
        FileName: Source filename for the schema definition.
        ContentType: Expected content/MIME type.
        Format: Storage format of the schema artifact. Always
            ``"json"`` — declarative JSON Schema descriptors are the
            only supported format.
        Created_On: UTC timestamp when the schema was registered.
        Updated_On: UTC timestamp of the last update.
    """

    Id: str
    ClassName: str
    Description: str
    FileName: str
    ContentType: str
    Format: Literal["json"] = Field(default="json")
    Created_On: Optional[datetime.datetime] = Field(default=None)
    Updated_On: Optional[datetime.datetime] = Field(default=None)
    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def parse_dates(cls, values):
        if "Created_On" in values and isinstance(values["Created_On"], str):
            values["Created_On"] = datetime.datetime.fromisoformat(
                values["Created_On"].replace("Z", "+00:00")
            ).astimezone(datetime.timezone.utc)
        if "Updated_On" in values and isinstance(values["Updated_On"], str):
            values["Updated_On"] = datetime.datetime.fromisoformat(
                values["Updated_On"].replace("Z", "+00:00")
            ).astimezone(datetime.timezone.utc)
        return values


class SchemaMetadata(BaseModel):
    """Lightweight reference to a schema within a schema set.

    Attributes:
        Id: Unique metadata identifier.
        SchemaId: Referenced schema identifier.
        Description: Human-readable description.
    """

    Id: str
    SchemaId: str
    Description: str

    model_config = ConfigDict(from_attributes=True)


class SchemaSet(BaseModel):
    """Named collection of schema references.

    Attributes:
        Id: Unique schema-set identifier.
        Name: Display name.
        Description: Human-readable description.
        Created_On: UTC timestamp of creation.
        Updated_On: UTC timestamp of last update.
        Schemas: Schema references belonging to this set.
    """

    Id: str
    Name: str
    Description: str
    Created_On: Optional[datetime.datetime] = Field(default=None)
    Updated_On: Optional[datetime.datetime] = Field(default=None)

    Schemas: list[SchemaMetadata] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class SchemaSetCreateRequest(BaseModel):
    """Request body for creating a new schema set.

    Attributes:
        Name: Display name of the new schema set.
        Description: Human-readable description.
    """

    Name: str
    Description: str


class SchemaSetAddSchemaRequest(BaseModel):
    """Request body for adding a schema to a schema set.

    Attributes:
        SchemaId: Identifier of the schema to add.
    """

    SchemaId: str


class SchemaVaultUnregisterResponse(BaseModel):
    """Response returned after unregistering a schema.

    Attributes:
        Status: Result status string.
        SchemaId: Identifier of the unregistered schema.
        ClassName: Python class name of the removed schema.
        FileName: Source filename of the removed schema.
    """

    Status: str
    SchemaId: str
    ClassName: str
    FileName: str

    def to_dict(self):
        return self.model_dump()


class SchemaVaultRegisterRequest(BaseModel):
    """Request body for registering a new schema.

    Attributes:
        ClassName: Python class name for the schema.
        Description: Human-readable description.
    """

    ClassName: str
    Description: str

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return cls(**json.loads(value))
        return value


class SchemaVaultUpdateRequest(BaseModel):
    """Request body for updating an existing schema.

    Attributes:
        SchemaId: Identifier of the schema to update.
        ClassName: New Python class name.
    """

    SchemaId: str
    ClassName: str

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return cls(**json.loads(value))
        return value


class SchemaVaultUnregisterRequest(BaseModel):
    """Request body for unregistering (deleting) a schema.

    Attributes:
        SchemaId: Identifier of the schema to remove.
    """

    SchemaId: str

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return cls(**json.loads(value))
        return value
