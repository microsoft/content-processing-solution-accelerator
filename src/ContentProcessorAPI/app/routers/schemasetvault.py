# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""FastAPI router for schema-set CRUD operations."""

from fastapi import APIRouter, Body, HTTPException, Request

from app.libs.base.typed_fastapi import TypedFastAPI
from app.routers.logics.schemasetvault import SchemaSets
from app.routers.models.schmavault.model import (
    Schema,
    SchemaSet,
    SchemaSetAddSchemaRequest,
    SchemaSetCreateRequest,
)

router = APIRouter(
    prefix="/schemasetvault",
    tags=["schemasetvault"],
    responses={404: {"description": "Not found"}},
)


@router.get(
    "/",
    response_model=list[SchemaSet],
    summary="List schema sets",
    description="""
    Returns all schema sets.

    ## Parameters
    None.

    ## Example Request Body
    Not applicable. This is a GET endpoint and does not accept a request body.

    Example request:
    `GET /schemasetvault/`
    """,
)
async def Get_All_Schema_Sets(
    request: Request = None,
) -> list[SchemaSet]:
    """List all schema sets."""
    app: TypedFastAPI = request.app  # type: ignore

    schemasets: SchemaSets = app.app_context.get_service(SchemaSets)
    return schemasets.GetAll()


@router.post(
    "/",
    response_model=SchemaSet,
    summary="Create a schema set",
    description="""
    Creates a schema set to group multiple registered schemas.

    ## Parameters
    - **Name** (body): Schema set name.
    - **Description** (body): Schema set description.

    ## Example Request Body
    ```json
    {
      "Name": "Claims",
      "Description": "Schemas used for processing claims"
    }
    ```
    """,
)
async def Create_Schema_Set(
    data: SchemaSetCreateRequest = Body(...),
    request: Request = None,
) -> SchemaSet:
    """Create a new schema set."""
    app: TypedFastAPI = request.app  # type: ignore

    schemasets: SchemaSets = app.app_context.get_service(SchemaSets)
    return schemasets.AddNew(data.Name, data.Description)


@router.get(
    "/{schemaset_id}",
    response_model=SchemaSet,
    summary="Get schema set details",
    description="""
    Returns a schema set by its ID.

    ## Parameters
    - **schemaset_id** (path): Schema set ID.

    ## Example Request Body
    Not applicable. This is a GET endpoint and does not accept a request body.

    Example request:
    `GET /schemasetvault/{schemaset_id}`
    """,
)
async def Get_Schema_Set_By_Id(
    schemaset_id: str,
    request: Request = None,
) -> SchemaSet:
    """Get schema set details by ID."""
    app: TypedFastAPI = request.app  # type: ignore
    schemasets: SchemaSets = app.app_context.get_service(SchemaSets)
    schemaset = schemasets.GetById(schemaset_id)
    if schemaset is None:
        raise HTTPException(status_code=404, detail="Schema Set not found")
    return schemaset


@router.delete(
    "/{schemaset_id}",
    summary="Delete a schema set",
    description="""
    Deletes a schema set by its ID.

    ## Parameters
    - **schemaset_id** (path): Schema set ID.

    ## Example Request Body
    Not applicable. This is a DELETE endpoint and does not accept a request body.

    Example request:
    `DELETE /schemasetvault/{schemaset_id}`
    """,
)
async def Delete_Schema_Set_By_Id(
    schemaset_id: str,
    request: Request = None,
):
    """Delete a schema set."""
    app: TypedFastAPI = request.app  # type: ignore

    schemasets: SchemaSets = app.app_context.get_service(SchemaSets)
    deleted = schemasets.DeleteById(schemaset_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Schema Set not found")

    return {"status": "success", "schemaset_id": schemaset_id}


@router.get(
    "/{schemaset_id}/schemas",
    response_model=list[Schema],
    summary="List schemas in a schema set",
    description="""
    Returns the schemas currently included in the given schema set.

    ## Parameters
    - **schemaset_id** (path): Schema set ID.

    ## Example Request Body
    Not applicable. This is a GET endpoint and does not accept a request body.

    Example request:
    `GET /schemasetvault/{schemaset_id}/schemas`
    """,
)
async def Get_All_Schemas_In_Set(
    schemaset_id: str,
    request: Request = None,
) -> list[Schema]:
    """List schemas inside a schema set."""
    app: TypedFastAPI = request.app  # type: ignore
    schemasets: SchemaSets = app.app_context.get_service(SchemaSets)
    try:
        return schemasets.GetAllSchemasInSet(schemaset_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "/{schemaset_id}/schemas",
    response_model=SchemaSet,
    summary="Add a schema to a schema set",
    description="""
    Adds an existing registered schema (by SchemaId) to a schema set.

    ## Parameters
    - **schemaset_id** (path): Schema set ID.
    - **SchemaId** (body): Registered schema ID to add.

    ## Example Request Body
    ```json
    {
      "SchemaId": "<schema_id>"
    }
    ```
    """,
)
async def Add_Schema_To_Set(
    schemaset_id: str,
    data: SchemaSetAddSchemaRequest = Body(...),
    request: Request = None,
) -> SchemaSet:
    """Add a schema to a schema set."""
    app: TypedFastAPI = request.app  # type: ignore
    schemasets: SchemaSets = app.app_context.get_service(SchemaSets)
    try:
        return schemasets.AddSchemaToSet(schemaset_id, data.SchemaId)
    except Exception as e:
        # Logic layer uses generic exceptions for not-found; map to 404.
        raise HTTPException(status_code=404, detail=str(e))


@router.delete(
    "/{schemaset_id}/schemas/{schema_id}",
    response_model=SchemaSet,
    summary="Remove a schema from a schema set",
    description="""
    Removes a schema (by schema_id) from the schema set.

    ## Parameters
    - **schemaset_id** (path): Schema set ID.
    - **schema_id** (path): Schema ID to remove.

    ## Example Request Body
    Not applicable. This is a DELETE endpoint and does not accept a request body.

    Example request:
    `DELETE /schemasetvault/{schemaset_id}/schemas/{schema_id}`
    """,
)
async def Remove_Schema_From_Set(
    schemaset_id: str,
    schema_id: str,
    request: Request = None,
) -> SchemaSet:
    """Remove a schema from a schema set."""
    app: TypedFastAPI = request.app  # type: ignore

    schemasets: SchemaSets = app.app_context.get_service(SchemaSets)
    try:
        return schemasets.RemoveSchemaFromSet(schemaset_id, schema_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
