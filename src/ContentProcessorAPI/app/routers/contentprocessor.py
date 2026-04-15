# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""FastAPI router for single-file content processing.

Exposes endpoints for submitting documents, polling processing status,
retrieving/updating/deleting processed results, and streaming the
original uploaded file.  Persists state in Cosmos DB and Azure Blob Storage.
"""

import datetime
import io
import logging
import urllib.parse
import uuid
from enum import Enum

from fastapi import APIRouter, Body, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pymongo.results import UpdateResult

from app.libs.base.typed_fastapi import TypedFastAPI
from app.libs.logging.event_utils import track_event_if_configured

logger = logging.getLogger(__name__)
from app.routers.logics.claimbatchpocessor import ClaimBatchProcessRepository
from app.utils.mime_types import MimeTypesDetection
from app.utils.upload_validation import (
    validate_upload_for_processing,
)

from .logics.contentprocessor import (
    ContentProcessor,
)
from .models.contentprocessor.content_process import (
    ContentProcess as CosmosContentProcess,
)
from .models.contentprocessor.content_process import (
    PaginatedResponse,
)
from .models.contentprocessor.model import (
    ArtifactType,
    ContentCommentUpdate,
    ContentProcess,
    ContentProcessorRequest,
    ContentResultDelete,
    ContentResultUpdate,
    Paging,
    ProcessFile,
    Status,
    Steps,
)

router = APIRouter(
    prefix="/contentprocessor",
    tags=["contentprocessor"],
    responses={404: {"description": "Not found"}},
)


class contentprocess_router_paths(str, Enum):
    submit = "/submit"
    status = "/status/{process_id}"
    delete = "/delete"
    update = "/update"
    comment = "/comment"
    get_original_file = "/processed/files/{process_id}"
    processed_contents = "/processed"
    processed_status = "/processed/{process_id}"
    processed_content_by_process_id = "/processed/{process_id}"
    processed_steps_content_by_process_id = "/processed/{process_id}/steps"
    processed_content_update_by_process_id = "/processed/{process_id}"
    processed_content_delete_by_process_id = "/processed/{process_id}"


@router.post(
    "/processed",
    response_model=PaginatedResponse,
    summary="List processed contents (paginated)",
    description="""
        Returns a list of processed content records with pagination support.

        This endpoint is commonly used to build a “Processed Contents” list screen.

        ## Parameters
        Pagination is provided in the request body.

        - **page_number**: The page number to retrieve (1-based index).
        - **page_size**: The number of items per page.

        Both fields are required and must be greater than 0.

        ## Example Request Body
        ```json
        {
            "page_number": 1,
            "page_size": 10
        }
        ```
    """,
)
async def get_all_processed_results(
    page_request: Paging,
    request: Request = None,
) -> PaginatedResponse:
    """Return a paginated list of processed content records."""
    app: TypedFastAPI = request.app  # type: ignore

    paged_cosmos_content_process = CosmosContentProcess.get_all_processes_from_cosmos(
        connection_string=app.app_context.configuration.app_cosmos_connstr,
        database_name=app.app_context.configuration.app_cosmos_database,
        collection_name=app.app_context.configuration.app_cosmos_container_process,
        page_number=page_request.page_number if page_request else 0,
        page_size=page_request.page_size if page_request else 0,
    )

    return paged_cosmos_content_process


@router.post(
    contentprocess_router_paths.submit,
    summary="Submit a file for processing",
    description="""
    Submits a single file to the content processor.

    The API validates the upload (filename sanitization, MIME sniffing, Content-Type checks,
    and size limits) before saving the file and enqueuing processing.

    The request must be sent as `multipart/form-data` with:
    - a JSON part (named `data`) that contains schema/metadata IDs
    - a file part (named `file`)

    ## Parameters
    - **Schema_Id** (body): Registered schema ID (UUID string).
    - **Metadata_Id** (body): Metadata identifier for the request.
    - **file** (form): PDF or image file (JPEG, BMP, GIF, PNG, TIFF). Max size: 20 MB.

    ## Example Request Body
    multipart/form-data
    - `data`: `{ "Schema_Id": "<schema_uuid>", "Metadata_Id": "<metadata_id>" }`
    - `file`: `<upload>`

   """,
)
async def Submit_File_With_MetaData(
    data: ContentProcessorRequest = Body(...),
    file: UploadFile = File(...),
    request: Request = None,
):
    """Submit a single file for processing.

    Performs strict validation of the upload (filename, MIME sniffing, Content-Type, size)
    before persisting to blob storage and enqueuing the processing message.
    """
    app: TypedFastAPI = request.app  # type: ignore
    validated = await validate_upload_for_processing(
        upload=file,
        max_filesize_mb=app.app_context.configuration.app_cps_max_filesize_mb,
    )
    if isinstance(validated, JSONResponse):
        return validated

    safe_filename, expected_for_ext, size_bytes = validated

    process_id = str(uuid.uuid4())

    schema_id = data.Schema_Id
    metadata_id = data.Metadata_Id

    content_processor: ContentProcessor = app.app_context.get_service(ContentProcessor)
    content_processor.save_file_to_blob(
        process_id=process_id, file=file.file, file_name=safe_filename
    )

    submit_queue_message = ContentProcess(**{
        "process_id": process_id,
        "files": [
            ProcessFile(**{
                "process_id": process_id,
                "id": str(uuid.uuid4()),
                "name": safe_filename,
                "size": size_bytes,
                "mime_type": expected_for_ext,
                "artifact_type": ArtifactType.SourceContent,
                "processed_by": "API",
            }),
        ],
        "pipeline_status": Status(**{
            "process_id": process_id,
            "schema_id": schema_id,
            "metadata_id": metadata_id,
            "creation_time": datetime.datetime.now(datetime.timezone.utc),
            "steps": [
                Steps.Extract,
                Steps.Mapping,
                Steps.Evaluating,
                Steps.Save,
            ],
            "remaining_steps": [
                Steps.Extract,
                Steps.Mapping,
                Steps.Evaluating,
                Steps.Save,
            ],
            "completed_steps": [],
        }),
    })

    content_processor.enqueue_message(submit_queue_message)

    track_event_if_configured("FileSubmitted", {
        "process_id": process_id,
        "file_name": safe_filename,
        "schema_id": schema_id,
        "metadata_id": metadata_id,
        "size_bytes": str(size_bytes),
    })

    file_size_mb = size_bytes / (1024 * 1024)

    status_url = f"/contentprocessor/status/{process_id}"

    CosmosContentProcess(
        process_id=process_id,
        processed_file_name=safe_filename,
        status="processing",
        imported_time=datetime.datetime.now(datetime.timezone.utc),
    ).update_process_status_to_cosmos(
        connection_string=app.app_context.configuration.app_cosmos_connstr,
        database_name=app.app_context.configuration.app_cosmos_database,
        collection_name=app.app_context.configuration.app_cosmos_container_process,
    )
    return JSONResponse(
        status_code=202,
        headers={"Location": status_url},
        content={
            "message": f"File '{safe_filename}' of size {file_size_mb:.2f} MB received with metadata: {data} \n The file is being processed.",
            "process_id": process_id,
            "status_url": status_url,
        },
    )


@router.get(
    contentprocess_router_paths.status,
    summary="Get file processing status",
    description="""
    Returns the status of a file being processed by the content processor.

    Once the file is processed, the status will be updated to `Completed` and the endpoint returns `302`.
    You can then fetch the processed result by calling `/contentprocessor/processed/{process_id}`.

    This endpoint is designed for async processing. After you submit a file via `/contentprocessor/submit`
    (which returns `202 Accepted`), you should poll this endpoint until you receive a terminal status.

    The status can be one of the following:

    - `processing`: The file is being processed (`200`).
    - `completed`: The file has been processed successfully (`302`).
    - `failed`: The process ID was not found (`404`).
    - `error`: The file processing failed (`500`).

    ## Parameters
    - **process_id** (path): Process ID returned by the submit endpoint.

    ## Example Request Body
    Not applicable. This is a GET endpoint and does not accept a request body.

    Example request:
    `GET /contentprocessor/status/{process_id}`

            """,
)
async def get_status(
    process_id: str,
    request: Request = None,
):
    """Return current processing status and redirect when complete."""
    app: TypedFastAPI = request.app  # type: ignore
    process_status = CosmosContentProcess(process_id=process_id).get_status_from_cosmos(
        connection_string=app.app_context.configuration.app_cosmos_connstr,
        database_name=app.app_context.configuration.app_cosmos_database,
        collection_name=app.app_context.configuration.app_cosmos_container_process,
    )

    track_event_if_configured("ProcessStatusQueried", {
        "process_id": process_id,
    })

    if process_status is None:
        return JSONResponse(
            status_code=404,
            content={
                "status": "failed",
                "process_id": process_id,
                "file_name": "",
                "message": f"Processing of file with Process ID '{process_id}' not found.",
            },
        )

    file_name = str(getattr(process_status, "processed_file_name", ""))

    if process_status.status == "Completed":
        return JSONResponse(
            status_code=302,
            content={
                "status": "completed",
                "process_id": process_id,
                "file_name": file_name,
                "message": f"Processing of file '{file_name}' with Process ID '{process_id}' is completed.",
                "resource_url": f"/contentprocessor/processes/{process_id}",
            },
        )
    elif process_status.status == "Error":
        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "process_id": process_id,
                "file_name": file_name,
                "message": f"Processing of file '{file_name}' with Process ID '{process_id}' has failed.",
            },
        )
    else:
        return JSONResponse(
            status_code=200,
            content={
                "status": process_status.status,
                "process_id": process_id,
                "file_name": file_name,
                "message": f"Processing of file '{file_name}' with Process ID '{process_id}' is still in progress.",
            },
        )


@router.get(
    contentprocess_router_paths.processed_content_by_process_id,
    response_model=CosmosContentProcess,
    summary="Get processed content result",
    description="""
    Returns the full processed content result for a given process ID.

    Use this endpoint to retrieve the complete processing result document (including step details).

    ## Parameters
    - **process_id** (path): Process ID to retrieve.

    ## Example Request Body
    Not applicable. This is a GET endpoint and does not accept a request body.

    Example request:
    `GET /contentprocessor/processed/{process_id}`
            """,
)
async def get_process(
    process_id: str,
    request: Request = None,
):
    """Return the full processed content document for *process_id*."""
    app: TypedFastAPI = request.app  # type: ignore

    process_status = CosmosContentProcess(process_id=process_id).get_status_from_cosmos(
        connection_string=app.app_context.configuration.app_cosmos_connstr,
        database_name=app.app_context.configuration.app_cosmos_database,
        collection_name=app.app_context.configuration.app_cosmos_container_process,
    )

    if not process_status:
        return JSONResponse(
            status_code=404,
            content={
                "status": "failed",
                "process_id": process_id,
                "file_name": "",
                "message": f"Processing of file with Process ID '{process_id}' not found.",
            },
        )

    return process_status


@router.get(
    contentprocess_router_paths.processed_steps_content_by_process_id,
    summary="Get processed step outputs",
    description="""
    Returns per-step processing outputs for a given process ID.

    Some step outputs can be too large to include in the main processed result. Use this endpoint
    to fetch step outputs separately and reduce payload sizes in the UI.

    ## Parameters
    - **process_id** (path): Process ID to retrieve step outputs for.

    ## Example Request Body
    Not applicable. This is a GET endpoint and does not accept a request body.

    Example request:
    `GET /contentprocessor/processed/{process_id}/steps`
            """,
)
async def get_process_steps(
    process_id: str,
    request: Request = None,
):
    """Return per-step processing outputs from blob storage."""
    app: TypedFastAPI = request.app  # type: ignore
    process_steps = CosmosContentProcess(process_id=process_id).get_status_from_blob(
        connection_string=app.app_context.configuration.app_storage_blob_url,
        blob_name="step_outputs.json",
        container_name=f"{app.app_context.configuration.app_cps_processes}/{process_id}",
    )

    if not process_steps:
        return JSONResponse(
            status_code=404,
            content={
                "status": "failed",
                "process_id": process_id,
                "file_name": "",
                "message": f"Processing of file with Process ID '{process_id}' not found.",
            },
        )

    return process_steps


@router.put(
    contentprocess_router_paths.processed_content_update_by_process_id,
    summary="Update processed result or comment",
    description="""
    Updates either (a) the stored processed result or (b) the process comment.

    Use this endpoint to:
    - correct/override extracted results (`ContentResultUpdate`), or
    - attach a user comment (`ContentCommentUpdate`).

    ## Parameters
    - **process_id** (path): Process ID to update.
    - **content_update_request** (body): Either `ContentResultUpdate` or `ContentCommentUpdate`.

    ## Example Request Body
    ContentResultUpdate:
        ```json
        {
            "process_id": "<process_id>",
            "modified_result": {
                "key": "value"
            }
        }
        ```

    ContentCommentUpdate:
        ```json
        {
            "process_id": "<process_id>",
            "comment": "This is a comment"
        }
        ```

            """,
)
async def update_process_result(
    process_id: str,
    content_update_request: ContentResultUpdate | ContentCommentUpdate,
    request: Request = None,
):
    """Update the processed result or attach a comment."""
    app: TypedFastAPI = request.app  # type: ignore
    update_response: UpdateResult = None

    if isinstance(content_update_request, ContentResultUpdate):
        update_response = CosmosContentProcess(
            process_id=process_id,
        ).update_process_result(
            connection_string=app.app_context.configuration.app_cosmos_connstr,
            database_name=app.app_context.configuration.app_cosmos_database,
            collection_name=app.app_context.configuration.app_cosmos_container_process,
            process_result=content_update_request.modified_result,
        )

    if isinstance(content_update_request, ContentCommentUpdate):
        update_response = CosmosContentProcess(
            process_id=process_id,
        ).update_process_comment(
            connection_string=app.app_context.configuration.app_cosmos_connstr,
            database_name=app.app_context.configuration.app_cosmos_database,
            collection_name=app.app_context.configuration.app_cosmos_container_process,
            comment=content_update_request.comment,
        )

    if not update_response:
        return JSONResponse(
            status_code=404,
            content={
                "status": "failed",
                "message": f"Processing of file with Process ID '{process_id}' not found.",
            },
        )
    else:
        track_event_if_configured("ProcessResultUpdated", {
            "process_id": process_id,
            "update_type": type(content_update_request).__name__,
        })
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"Processing of file with Process ID '{process_id}' updated.",
            },
        )


@router.get(
    contentprocess_router_paths.get_original_file,
    summary="Stream original uploaded file",
    description="""
    Streams the original uploaded file for a given process ID.

    This endpoint is intended for inline viewing (e.g., in a document viewer). It returns a
    streaming response with an appropriate content type.

    ## Parameters
    - **process_id** (path): Process ID of the original upload.

    ## Example Request Body
    Not applicable. This is a GET endpoint and does not accept a request body.

    Example request:
    `GET /contentprocessor/processed/files/{process_id}`
            """,
)
async def get_original_file(process_id: str, request: Request = None):
    """Stream the originally uploaded file for inline viewing."""
    app: TypedFastAPI = request.app  # type: ignore
    process_status = CosmosContentProcess(process_id=process_id).get_status_from_cosmos(
        connection_string=app.app_context.configuration.app_cosmos_connstr,
        database_name=app.app_context.configuration.app_cosmos_database,
        collection_name=app.app_context.configuration.app_cosmos_container_process,
    )

    if process_status is None:
        return JSONResponse(
            status_code=404,
            content={
                "status": "failed",
                "message": f"Processing of file with Process ID '{process_id}' not found.",
            },
        )

    if process_status is not None:
        file_bytes = process_status.get_file_bytes_from_blob(
            connection_string=app.app_context.configuration.app_storage_blob_url,
            blob_name=process_status.processed_file_name,
            container_name=f"{app.app_context.configuration.app_cps_processes}/{process_status.process_id}",
        )
        file_stream = io.BytesIO(file_bytes)

        encoded_filename = urllib.parse.quote(process_status.processed_file_name)
        content_type_string = MimeTypesDetection.get_file_type(
            process_status.processed_file_name
        )
        headers = {
            "Content-Disposition": f"inline; filename*=UTF-8''{encoded_filename}",
            "Content-Type": content_type_string,
        }

        return StreamingResponse(
            file_stream, media_type=content_type_string, headers=headers
        )


@router.delete(
    contentprocess_router_paths.processed_content_delete_by_process_id,
    response_model=ContentResultDelete,
    summary="Delete processed content result",
    description="""
    Deletes the processed content record for a given process ID.

    This removes the record and related artifacts (when applicable).

    ## Parameters
    - **process_id** (path): Process ID to delete.

    ## Example Request Body
    Not applicable. This is a DELETE endpoint and does not accept a request body.

    Example request:
    `DELETE /contentprocessor/processed/{process_id}`
            """,
)
async def delete_processed_file(
    process_id: str, request: Request = None
) -> ContentResultDelete:
    """Delete the processed content record and related artifacts."""
    app: TypedFastAPI = request.app  # type: ignore
    try:
        deleted_file = CosmosContentProcess(
            process_id=process_id
        ).delete_processed_file(
            connection_string=app.app_context.configuration.app_cosmos_connstr,
            database_name=app.app_context.configuration.app_cosmos_database,
            collection_name=app.app_context.configuration.app_cosmos_container_process,
            storage_connection_string=app.app_context.configuration.app_storage_blob_url,
            container_name=app.app_context.configuration.app_cps_processes,
        )

        claim_process_repository = app.app_context.get_service(
            ClaimBatchProcessRepository
        )
        await claim_process_repository.delete_async(process_id)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return ContentResultDelete(
        status="Success" if deleted_file else "Failed",
        process_id=deleted_file.process_id if deleted_file else "",
        message="" if deleted_file else "This record no longer exists. Please refresh.",
    )
