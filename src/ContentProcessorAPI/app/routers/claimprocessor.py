# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""FastAPI router for claim batch lifecycle management.

Exposes endpoints for creating claim containers, uploading files into them,
submitting batches for processing, and querying/deleting claim results.
Delegates business logic to ClaimBatchProcessor and persists state via
ClaimBatchProcessRepository.
"""

import logging
import uuid
from enum import Enum

from fastapi import APIRouter, Body, File, Request, UploadFile
from fastapi.responses import JSONResponse
from sas.cosmosdb.base.repository_base import SortDirection
from sas.cosmosdb.mongo.repository import SortField

from app.libs.base.typed_fastapi import TypedFastAPI
from app.libs.logging.event_utils import track_event_if_configured
from app.routers.logics.claimbatchpocessor import (
    ClaimBatchProcessor,
    ClaimBatchProcessRepository,
)
from app.routers.models.contentprocessor.claim_process import (
    Claim_Process,
    Claim_Steps,
    PaginatedClaimProcessResponse,
)
from app.routers.models.contentprocessor.model import (
    ClaimProcessRequest,
    ContentProcessorBatchFileAddRequest,
    Paging,
)
from app.utils.upload_validation import validate_upload_for_processing

from .models.contentprocessor.claim import (
    ClaimCreateRequest,
    ClaimItem,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/claimprocessor",
    tags=["claimprocessor"],
    responses={404: {"description": "Not found"}},
)


class claimprocessor_router_paths(str, Enum):
    create_claim = "/claims"
    get_claim_manifest = "/claims/{claim_id}/manifest"
    delete_claim = "/claims/{claim_id}"
    add_file_to_claim = "/claims/{claim_id}/files"

    start_process = "/claims"
    get_all_processed_batches = "/claims/processed"
    status = "/claims/{claim_id}/status"
    delete = "/claims/{claim_id}"
    add_comment = "/claims/{claim_id}/comment"
    retrieve_claim_details = "/claims/{claim_id}"


@router.put(
    claimprocessor_router_paths.create_claim,
    summary="Create a claim batch",
    description="""
    Creates a new batch container for grouping multiple uploads into one claim process.

    Typical client flow:
    1) Create a batch.
    2) Upload one or more files into the batch.
    3) Submit the batch for processing.

    ## Parameters
    - **schema_collection_id** (body): Schema set / collection identifier used for the batch.

    ## Example Request Body
    ```json
    {
      "schema_collection_id": "<schemaset_id>"
    }
    ```
    """,
)
async def create_claim_container(
    claim_creation_request: ClaimCreateRequest, request: Request = None
):
    """Create a new empty claim container for grouping uploads."""
    app: TypedFastAPI = request.app  # type: ignore

    batch_processor: ClaimBatchProcessor = app.app_context.get_service(
        ClaimBatchProcessor
    )
    new_batch_process = batch_processor.create_claim_container(
        schemaset_id=claim_creation_request.schema_collection_id
    )

    return JSONResponse(
        status_code=200,
        content=new_batch_process.model_dump(mode="json"),
    )


@router.get(
    claimprocessor_router_paths.get_claim_manifest,
    summary="Get claim batch details",
    description="""
    Returns the batch manifest for the given batch ID.

    ## Parameters
    - **batch_id** (path): Batch identifier.

    ## Example Request Body
    Not applicable. This is a GET endpoint and does not accept a request body.

    Example request:
    `GET /claimprocessor/batches/{batch_id}`
    """,
)
async def get_claim_manifest(claim_id: str, request: Request = None):
    """Return the manifest for a claim container."""
    app: TypedFastAPI = request.app  # type: ignore

    claim_processor: ClaimBatchProcessor = app.app_context.get_service(
        ClaimBatchProcessor
    )
    try:
        claim = claim_processor.get_claim_manifest(claim_id=claim_id)
    except Exception:
        claim = None

    if claim is None:
        return JSONResponse(
            status_code=404,
            content={
                "status": "failed",
                "message": f"Claim '{claim_id}' not found.",
            },
        )

    return JSONResponse(status_code=200, content=claim.model_dump(mode="json"))


@router.delete(
    claimprocessor_router_paths.delete_claim,
    summary="Delete a claim batch",
    description="""
    Deletes the batch container and associated manifest.

    ## Parameters
    - **claim_id** (path): Claim identifier.

    ## Example Request Body
    Not applicable. This is a DELETE endpoint and does not accept a request body.

    Example request:
    `DELETE /claimprocessor/claims/{claim_id}`
    """,
)
async def delete_claim_container(claim_id: str, request: Request = None):
    """Delete a claim container and its associated batch-process record."""
    app: TypedFastAPI = request.app  # type: ignore

    claim_processor: ClaimBatchProcessor = app.app_context.get_service(
        ClaimBatchProcessor
    )
    try:
        claim_processor.delete_claim_container(claim_id=claim_id)
    except Exception as ex:
        # Best-effort cleanup: continue deleting the claim-process record even if
        # the backing claim container is already missing or cannot be deleted.
        print(f"Failed to delete claim container for '{claim_id}': {ex}")

    batch_process_repository: ClaimBatchProcessRepository = app.app_context.get_service(
        ClaimBatchProcessRepository
    )

    if await batch_process_repository.get_async(claim_id) is None:
        return JSONResponse(
            status_code=404,
            content={
                "status": "failed",
                "message": f"Claim process with ID {claim_id} not found.",
            },
        )

    await batch_process_repository.delete_async(key=claim_id)

    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "message": f"Claim process with ID : '{claim_id}' and its container have been deleted.",
        },
    )


@router.post(
    claimprocessor_router_paths.add_file_to_claim,
    summary="Upload a file to a claim",
    description="""
    Uploads a file into an existing claim container.

    The API reuses the same strict upload validation as the content processor submit endpoint.
    The request must be sent as `multipart/form-data` with:
    - a JSON part (named `data`) identifying the claim and schema/metadata IDs
    - a file part (named `file`)

    ## Parameters
    - **Claim_Id** (body): Target claim ID.
    - **Schema_Id** (body): Schema ID for this file.
    - **Metadata_Id** (body): Metadata ID for this file.
    - **file** (form): PDF or image file (max size controlled by server configuration).

    ## Example Request Body
    multipart/form-data
    - `data`: `{ "Claim_Id": "<claim_id>", "Schema_Id": "<schema_id>", "Metadata_Id": "<metadata_id>" }`
    - `file`: `<upload>`
    """,
)
async def add_file_to_claim(
    claim_id: str,
    data: ContentProcessorBatchFileAddRequest = Body(...),
    file: UploadFile = File(...),
    request: Request = None,
):
    """Upload a file into an existing claim container.

    This endpoint reuses the same file validation logic as `/contentprocessor/submit`.
    It stores the file in the claim's blob prefix and returns basic metadata.
    """
    app: TypedFastAPI = request.app  # type: ignore

    validated = await validate_upload_for_processing(
        upload=file,
        max_filesize_mb=app.app_context.configuration.app_cps_max_filesize_mb,
    )

    if isinstance(validated, JSONResponse):
        return validated

    # Path param must match the body payload to prevent misrouted uploads.
    if data.Claim_Id != claim_id:
        return JSONResponse(
            status_code=400,
            content={
                "status": "failed",
                "message": "Path claim_id must match data.Claim_Id.",
            },
        )

    safe_filename, expected_mime_type, size_bytes = validated
    file_bytes = await file.read()

    batch_processor: ClaimBatchProcessor = app.app_context.get_service(
        ClaimBatchProcessor
    )
    batch_processor.add_file_to_claim(
        claim_id=claim_id,
        file_name=safe_filename,
        file_content=file_bytes,
    )

    batch_processor.add_claim_item(
        claim_id=claim_id,
        claim_item=ClaimItem(
            id=str(uuid.uuid4()),
            claim_id=claim_id,
            schema_id=data.Schema_Id,
            metadata_id=data.Metadata_Id,
            file_name=safe_filename,
            size=size_bytes,
            mime_type=expected_mime_type,
        ),
    )

    return JSONResponse(
        status_code=200,
        content={
            "batch_id": claim_id,
            "file_name": safe_filename,
            "size": size_bytes,
            "mime_type": expected_mime_type,
        },
    )


@router.post(
    claimprocessor_router_paths.start_process,
    summary="Submit claim batch for processing",
    description="""
    Submits a claim batch Id for processing to the Claim Processor.

    This validates the batch ID and enqueues a processing message.

    ## Parameters
    - **batch_process_id** (body): Batch process ID to enqueue for processing.
    - **metadata_id** (body, optional): Metadata identifier (if applicable).

    ## Example Request Body
    ```json
    {
      "batch_process_id": "<batch_process_id>",
      "metadata_id": "<metadata_id>"
    }
    ```
    """,
)
async def start_claim_process(
    data: ClaimProcessRequest = Body(...),
    request: Request = None,
):
    """Submit a claim batch Id for processing to the Claim Processor.

    The batch Id is validated, and a processing message is enqueued.
    """
    app: TypedFastAPI = request.app  # type: ignore

    batch_processor: ClaimBatchProcessor = app.app_context.get_service(
        ClaimBatchProcessor
    )
    claim_process_repository: ClaimBatchProcessRepository = app.app_context.get_service(
        ClaimBatchProcessRepository
    )

    try:
        batch_processor.enqueue_claim_request_for_processing(claim_process_request=data)
    except Exception as e:
        track_event_if_configured("ClaimProcessError", {
            "claim_id": data.claim_process_id,
            "error": str(e),
            "error_type": type(e).__name__,
        })
        return JSONResponse(
            status_code=400,
            content={
                "status": "failed",
                "message": str(e),
            },
        )

    if await claim_process_repository.get_async(data.claim_process_id) is not None:
        await claim_process_repository.delete_async(data.claim_process_id)

    await claim_process_repository.add_async(
        Claim_Process(
            id=data.claim_process_id,
            process_name="Waiting for processing",
            schemaset_id="",
            status=Claim_Steps.PENDING,
        )
    )

    track_event_if_configured("ClaimProcessSubmitted", {
        "claim_id": data.claim_process_id,
    })

    return JSONResponse(
        status_code=202,
        headers={"Location": f"/claims/{data.claim_process_id}/status"},
        content={
            "status": "success",
            "message": f"claim id '{data.claim_process_id}' has been submitted for processing.",
            "location": f"/claims/{data.claim_process_id}/status",
        },
    )


@router.get(
    claimprocessor_router_paths.status,
    summary="Get claim batch processing status",
    description="""
    Returns the processing status for a claim batch process.

    This endpoint is designed for asynchronous processing. Submit a batch and poll this endpoint
    until processing completes.

    Common outcomes:
    - `200`: Still processing.
    - `304`: Completed.
    - `404`: Claim batch process ID not found.

    ## Parameters
    - **claim_id** (path): Claim batch process ID.

    ## Example Request Body
    Not applicable. This is a GET endpoint and does not accept a request body.

    Example request:
    `GET /claimprocessor/claims/{claim_id}/status`
    """,
)
async def get_claim_status(claim_id: str, request: Request = None):
    """Return the current processing status for a claim batch."""
    app: TypedFastAPI = request.app  # type: ignore

    claim_process_repository: ClaimBatchProcessRepository = app.app_context.get_service(
        ClaimBatchProcessRepository
    )
    claim_process: Claim_Process = await claim_process_repository.get_async(claim_id)
    if not claim_process:
        return JSONResponse(
            status_code=404,
            content={
                "status": "Not Found",
                "message": f"Claim process with ID {claim_id} not found.",
            },
        )
    else:
        if claim_process.status == "Completed":
            return JSONResponse(
                status_code=302,
                headers={"Location": f"/claimprocessor/claims/{claim_id}"},
                content={
                    "status": claim_process.status,
                    "message": f"Claim Batch '{claim_id}' has been completed.",
                    "location": f"/claimprocessor/claims/{claim_id}",
                },
            )
        elif claim_process.status == "Failed":
            return JSONResponse(
                status_code=302,
                headers={"Location": f"/claimprocessor/claims/{claim_id}"},
                content={
                    "status": claim_process.status,
                    "message": "Workflow execution failed. I cannot help with this request as it involves content that violates our content safety guidelines. Please upload a another file for auto claim processing",
                    "location": f"/claimprocessor/claims/{claim_id}",
                },
            )
        else:
            return JSONResponse(
                status_code=200,
                content={
                    "status": claim_process.status,
                    "message": f"Claim Batch '{claim_id}' is in progress.",
                },
            )


@router.delete(
    claimprocessor_router_paths.delete,
    summary="Delete claim batch process",
    description="""
    Deletes a claim batch process by its ID.

    ## Parameters
    - **claim_id** (path): Claim batch process ID.

    ## Example Request Body
    Not applicable. This is a DELETE endpoint and does not accept a request body.

    Example request:
    `DELETE /claimprocessor/claims/{claim_id}`
    """,
)
async def delete_claim_process(claim_id: str, request: Request = None):
    """Delete a claim batch process record."""
    app: TypedFastAPI = request.app  # type: ignore

    batch_process_repository: ClaimBatchProcessRepository = app.app_context.get_service(
        ClaimBatchProcessRepository
    )

    if await batch_process_repository.get_async(claim_id) is None:
        return JSONResponse(
            status_code=404,
            content={
                "status": "failed",
                "message": f"Claim Batch process with ID {claim_id} not found.",
            },
        )

    await batch_process_repository.delete_async(claim_id)

    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "message": f"Claim process with ID {claim_id} has been deleted.",
        },
    )


@router.post(
    claimprocessor_router_paths.add_comment,
    summary="Add comment to claim batch process",
    description="""
    Stores a user comment on an existing claim batch process.

    ## Parameters
    - **claim_id** (path): Claim batch process ID.
    - **comment** (body): Comment text.

    ## Example Request Body
    ```json
    {
      "comment": "This is a comment"
    }
    """,
)
async def add_comment_to_claim(
    claim_id: str,
    comment: str = Body(..., embed=True),
    request: Request = None,
):
    """Attach a user comment to an existing claim batch process."""
    app: TypedFastAPI = request.app  # type: ignore

    batch_process_repository: ClaimBatchProcessRepository = app.app_context.get_service(
        ClaimBatchProcessRepository
    )

    claim_process: Claim_Process = await batch_process_repository.get_async(claim_id)
    if not claim_process:
        return JSONResponse(
            status_code=404,
            content={
                "status": "failed",
                "message": f"Claim process with ID {claim_id} not found.",
            },
        )

    claim_process.process_comment = comment
    await batch_process_repository.update_async(claim_process)

    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "message": f"Comment added to Claim Batch process with ID {claim_id}.",
        },
    )


@router.get(
    claimprocessor_router_paths.retrieve_claim_details,
    summary="Get claim batch process details",
    description="""
    Returns the full claim batch process document.

    ## Parameters
    - **claim_id** (path): Claim batch process ID.

    ## Example Request Body
    Not applicable. This is a GET endpoint and does not accept a request body.

    Example request:
    `GET /claimprocessor/claims/{claim_id}`
    """,
)
async def retrieve_claim_details(claim_id: str, request: Request = None):
    """Return the full claim batch process document."""
    app: TypedFastAPI = request.app  # type: ignore

    batch_process_repository: ClaimBatchProcessRepository = app.app_context.get_service(
        ClaimBatchProcessRepository
    )

    claim_process: Claim_Process = await batch_process_repository.get_async(claim_id)
    if not claim_process:
        return JSONResponse(
            status_code=404,
            content={
                "status": "failed",
                "message": f"Claim Batch process with ID {claim_id} not found.",
            },
        )

    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "data": claim_process.model_dump(mode="json"),
        },
    )


@router.post(
    claimprocessor_router_paths.get_all_processed_batches,
    summary="List claim batch processes (paginated)",
    description="""
    Returns a paginated list of claim batch processes.

    This endpoint is typically used to build a “Claim Processing History” list screen.

    ## Parameters
    - **page_number** (body): Page number to retrieve (1-based).
    - **page_size** (body): Number of items per page.

    ## Example Request Body
    ```json
    {
      "page_number": 1,
      "page_size": 10
    }
    ```
    """,
)
async def get_all_claim_batches(
    page_request: Paging = Body(...), request: Request = None
):
    """Return a paginated list of claim batch processes."""
    app: TypedFastAPI = request.app  # type: ignore

    batch_process_repository: ClaimBatchProcessRepository = app.app_context.get_service(
        ClaimBatchProcessRepository
    )
    total_count = await batch_process_repository.count_async({})
    total_pages = (
        (total_count + page_request.page_size - 1) // page_request.page_size
        if page_request.page_size > 0
        else 1
    )

    skip = (page_request.page_number - 1) * page_request.page_size
    # Don't fetch large size of fields - summary and gapanalysis result in list
    claim_processes = await batch_process_repository.find_with_pagination_async(
        predicate={},
        sort_fields=[SortField("process_time", SortDirection.DESCENDING)],
        skip=skip,
        limit=page_request.page_size,
        projection={
            "_id": False,
            "id": True,
            "process_name": True,
            "schemaset_id": True,
            "metadata_id": True,
            "processed_documents": True,
            "status": True,
            "process_time": True,
            "processed_time": True,
            "process_comment": True,
        },
    )

    return JSONResponse(
        status_code=200,
        content=PaginatedClaimProcessResponse(
            total_count=total_count,
            total_pages=total_pages,
            current_page=page_request.page_number,
            page_size=page_request.page_size,
            items=claim_processes,
        ).model_dump(mode="json"),
    )
