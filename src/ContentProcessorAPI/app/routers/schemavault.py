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
from app.routers.logics.schema_validator import (
    SchemaValidationError,
    derive_class_name,
    validate_json_schema,
)
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

#: Filename extensions accepted by the schema-vault upload routes.
#: Only ``.json`` (declarative JSON Schema) is supported. The legacy
#: ``.py`` (executable Pydantic class) format was removed because the
#: worker would ``exec`` uploaded code, exposing an RCE primitive
#: against any caller able to register a schema.
_ALLOWED_EXTENSIONS: tuple[str, ...] = (".json",)
_MAX_UPLOAD_BYTES: int = 1 * 1024 * 1024


def _validate_upload(file: UploadFile) -> tuple[str, str]:
    """Common upload checks for ``POST`` and ``PUT`` schema endpoints.

    Returns a ``(safe_filename, extension)`` tuple. Raises ``HTTPException``
    with the appropriate status on any failure.
    """
    try:
        safe_filename = sanitize_filename(file.filename)
    except ValueError:
        raise HTTPException(status_code=400, detail="Filename is too long.")

    extension = os.path.splitext(safe_filename)[1].lower()
    if extension not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=(
                "Unsupported schema file type. Only .json schema files "
                "are accepted; legacy .py uploads are disabled."
            ),
        )

    size_bytes = get_upload_size_bytes(file)
    if size_bytes is None:
        raise HTTPException(status_code=400, detail="Unable to determine upload size.")

    if size_bytes > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413, detail="Schema file is too large (max 1 MB)."
        )

    return safe_filename, extension


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
    Registers a new schema file (`.py` or `.json`) and stores its metadata
    in the Schema Vault.

    The request must be sent as `multipart/form-data` with:
    - a JSON part (named `data`)
    - a file part (named `file`)

    Constraints:
    - Accepted extensions: `.py` (legacy executable Python class) and
      `.json` (declarative JSON Schema; recommended).
    - Max size: 1 MB.

    For `.json` uploads:
    - Must be a valid JSON Schema (Draft 2020-12) with `type: "object"`
      and a `properties` block.
    - The `ClassName` field in the request body is ignored if the JSON
      document declares a `title`; otherwise the filename stem is used.

    ## Parameters
    - **ClassName** (body): Schema class name. Used for `.py` uploads and
      as a fallback for `.json` uploads without a `title`.
    - **Description** (body): Human-readable description.
    - **file** (form): `.py` or `.json` schema file (max 1 MB).

    ## Example Request Body
    multipart/form-data
    - `data`: `{ "ClassName": "InvoiceSchema", "Description": "Extract invoice fields" }`
    - `file`: `<schema.py>` or `<schema.json>`
    """,
)
async def Register_Schema(
    data: SchemaVaultRegisterRequest = Body(...),
    file: UploadFile = File(...),
    request: Request = None,
) -> Schema:
    """Register a new schema file into the vault."""
    app: TypedFastAPI = request.app  # type: ignore

    schemas: Schemas = app.app_context.get_service(Schemas)

    safe_filename, extension = _validate_upload(file)

    raw = file.file.read()
    file.file.seek(0)
    try:
        document = validate_json_schema(raw)
    except SchemaValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail={"message": "Invalid JSON schema.", "errors": exc.errors},
        ) from exc

    fallback = os.path.splitext(safe_filename)[0]
    class_name = derive_class_name(document, fallback=data.ClassName or fallback)
    content_type = file.content_type or "application/json"

    return schemas.Add(
        file,
        Schema(
            Id=str(uuid.uuid4()),
            ClassName=class_name,
            Description=data.Description,
            FileName=safe_filename,
            ContentType=content_type,
            Format="json",
        ),
    )


@router.put(
    "/",
    response_model=Schema,
    summary="Update a schema",
    description="""
    Updates an existing registered schema (`.py` or `.json` file) and
    associated metadata.

    The request must be sent as `multipart/form-data` with:
    - a JSON part (named `data`)
    - a file part (named `file`)

    Constraints:
    - Accepted extensions: `.py` and `.json`.
    - Max size: 1 MB.

    ## Parameters
    - **SchemaId** (body): Schema ID to update.
    - **ClassName** (body): Updated class name (fallback for `.json`
      schemas without a `title`).
    - **file** (form): New `.py` or `.json` schema file (max 1 MB).

    ## Example Request Body
    multipart/form-data
    - `data`: `{ "SchemaId": "<schema_id>", "ClassName": "InvoiceSchema" }`
    - `file`: `<schema.py>` or `<schema.json>`
    """,
)
async def Update_Schema(
    data: SchemaVaultUpdateRequest = Body(...),
    file: UploadFile = File(...),
    request: Request = None,
) -> Schema:
    """Update an existing schema with a new file."""
    app: TypedFastAPI = request.app  # type: ignore

    safe_filename, extension = _validate_upload(file)

    raw = file.file.read()
    file.file.seek(0)
    try:
        document = validate_json_schema(raw)
    except SchemaValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail={"message": "Invalid JSON schema.", "errors": exc.errors},
        ) from exc
    fallback = os.path.splitext(safe_filename)[0]
    class_name = derive_class_name(document, fallback=data.ClassName or fallback)

    schemas: Schemas = app.app_context.get_service(Schemas)
    return schemas.Update(file, data.SchemaId, class_name, "json")


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
