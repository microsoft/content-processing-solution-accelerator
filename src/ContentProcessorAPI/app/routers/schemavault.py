# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""FastAPI router for individual schema registration and management."""

import io
import os
import urllib.parse
import uuid

from fastapi import APIRouter, Body, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import StreamingResponse

from app.libs.base.typed_fastapi import TypedFastAPI
from app.routers.logics.schemavault import Schemas
from app.routers.models.schmavault.model import (
    Schema,
    SchemaVaultRegisterRequest,
    SchemaVaultUnregisterRequest,
    SchemaVaultUnregisterResponse,
    SchemaVaultUpdateRequest,
)
from app.utils.upload_validation import get_upload_size_bytes, sanitize_filename

router = APIRouter(
    prefix="/schemavault",
    tags=["schemavault"],
    responses={404: {"description": "Not found"}},
)


@router.get(
    "/",
    response_model=list[Schema],
    summary="List registered schemas",
    description="""
    Returns all schemas registered in the Schema Vault.

    ## Parameters
    None.

    ## Example Request Body
    Not applicable. This is a GET endpoint and does not accept a request body.

    Example request:
    `GET /schemavault/`
    """,
)
async def Get_All_Registered_Schema(
    request: Request = None,
) -> list[Schema]:
    """List all schemas registered in the vault."""
    app: TypedFastAPI = request.app  # type: ignore

    schemas: Schemas = app.app_context.get_service(Schemas)
    return schemas.GetAll()


@router.post(
    "/",
    response_model=Schema,
    summary="Register a schema",
    description="""
    Registers a new schema file (`.py`) and stores its metadata in the Schema Vault.

    The request must be sent as `multipart/form-data` with:
    - a JSON part (named `data`)
    - a file part (named `file`)

    Constraints:
    - Only `.py` files are accepted.
    - Max size: 1 MB.

    ## Parameters
    - **ClassName** (body): Schema class name contained in the uploaded file.
    - **Description** (body): Human-readable description.
    - **file** (form): `.py` schema file (max 1 MB).

    ## Example Request Body
    multipart/form-data
    - `data`: `{ "ClassName": "InvoiceSchema", "Description": "Extract invoice fields" }`
    - `file`: `<schema.py>`
    """,
)
async def Register_Schema(
    data: SchemaVaultRegisterRequest = Body(...),
    file: UploadFile = File(...),
    request: Request = None,
) -> Schema:
    """Register a new schema file (.py) into the vault."""
    app: TypedFastAPI = request.app  # type: ignore

    schemas: Schemas = app.app_context.get_service(Schemas)
    try:
        safe_filename = sanitize_filename(file.filename)
    except ValueError:
        raise HTTPException(status_code=400, detail="Filename is too long.")

    extension = os.path.splitext(safe_filename)[1].lower()
    if extension != ".py":
        raise HTTPException(
            status_code=415,
            detail="Unsupported schema file type. Only .py schema files are supported.",
        )

    size_bytes = get_upload_size_bytes(file)
    if size_bytes is None:
        raise HTTPException(status_code=400, detail="Unable to determine upload size.")

    # Schemas are small config artifacts; keep a conservative cap.
    if size_bytes > 1 * 1024 * 1024:
        raise HTTPException(
            status_code=413, detail="Schema file is too large (max 1 MB)."
        )

    return schemas.Add(
        file,
        Schema(
            Id=str(uuid.uuid4()),
            ClassName=data.ClassName,
            Description=data.Description,
            FileName=safe_filename,
            ContentType=file.content_type,
        ),
    )


@router.put(
    "/",
    response_model=Schema,
    summary="Update a schema",
    description="""
    Updates an existing registered schema (`.py` file) and associated metadata.

    The request must be sent as `multipart/form-data` with:
    - a JSON part (named `data`)
    - a file part (named `file`)

    Constraints:
    - Only `.py` files are accepted.
    - Max size: 1 MB.

    ## Parameters
    - **SchemaId** (body): Schema ID to update.
    - **ClassName** (body): Updated class name.
    - **file** (form): New `.py` schema file (max 1 MB).

    ## Example Request Body
    multipart/form-data
    - `data`: `{ "SchemaId": "<schema_id>", "ClassName": "InvoiceSchema" }`
    - `file`: `<schema.py>`
    """,
)
async def Update_Schema(
    data: SchemaVaultUpdateRequest = Body(...),
    file: UploadFile = File(...),
    request: Request = None,
) -> Schema:
    """Update an existing schema with a new file."""
    app: TypedFastAPI = request.app  # type: ignore
    try:
        safe_filename = sanitize_filename(file.filename)
    except ValueError:
        raise HTTPException(status_code=400, detail="Filename is too long.")

    extension = os.path.splitext(safe_filename)[1].lower()
    if extension != ".py":
        raise HTTPException(
            status_code=415,
            detail="Unsupported schema file type. Only .py schema files are supported.",
        )

    size_bytes = get_upload_size_bytes(file)
    if size_bytes is None:
        raise HTTPException(status_code=400, detail="Unable to determine upload size.")

    if size_bytes > 1 * 1024 * 1024:
        raise HTTPException(
            status_code=413, detail="Schema file is too large (max 1 MB)."
        )

    schemas: Schemas = app.app_context.get_service(Schemas)
    return schemas.Update(file, data.SchemaId, data.ClassName)


@router.delete(
    "/",
    summary="Unregister a schema",
    description="""
    Removes a schema from the vault by schema ID.

    ## Parameters
    - **SchemaId** (body): Schema ID to delete.

    ## Example Request Body
    ```json
    {
      "SchemaId": "<schema_id>"
    }
    ```
    """,
)
async def Unregister_Schema(
    data: SchemaVaultUnregisterRequest,
    request: Request = None,
) -> SchemaVaultUnregisterResponse:
    """Unregister (delete) a schema by ID."""
    app: TypedFastAPI = request.app  # type: ignore

    schemas: Schemas = app.app_context.get_service(Schemas)
    try:
        deleted_schema = schemas.Delete(data.SchemaId)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return SchemaVaultUnregisterResponse(**{
        "Status": "Success",
        "SchemaId": deleted_schema.Id,
        "ClassName": deleted_schema.ClassName,
        "FileName": deleted_schema.FileName,
    })


@router.get(
    "/schemas/{schema_id}",
    summary="Download schema file",
    description="""
    Downloads the schema source file for a registered schema ID.

    ## Parameters
    - **schema_id** (path): Registered schema ID.

    ## Example Request Body
    Not applicable. This is a GET endpoint and does not accept a request body.

    Example request:
    `GET /schemavault/schemas/{schema_id}`
    """,
)
async def Get_Registered_Schema_File_By_Schema_Id(
    schema_id: str,
    response: Response,
    request: Request = None,
):
    """Download a registered schema file by schema ID."""
    app: TypedFastAPI = request.app  # type: ignore

    schemas: Schemas = app.app_context.get_service(Schemas)
    try:
        schemas = schemas.GetFile(schema_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    encoded_filename = urllib.parse.quote(schemas["FileName"])

    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
        "Content-Type": schemas["ContentType"],
    }

    file_stream = io.BytesIO(schemas["File"])

    return StreamingResponse(
        content=file_stream, media_type=schemas["ContentType"], headers=headers
    )
