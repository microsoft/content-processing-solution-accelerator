# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import datetime
import io
import urllib.parse
import uuid

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pymongo.results import UpdateResult

from app.appsettings import AppConfiguration, get_app_config
from app.routers.logics.contentprocessor import (
    ContentProcessor,
    get_content_processor,
)
from app.routers.models.contentprocessor.content_process import (
    ContentProcess as CosmosContentProcess,
)
from app.routers.models.contentprocessor.content_process import (
    PaginatedResponse,
)
from app.routers.models.contentprocessor.mime_types import MimeTypes, MimeTypesDetection
from app.routers.models.contentprocessor.model import (
    ArtifactType,
    ContentCommentUpdate,
    ContentProcess,
    ContentProcessorRequest,
    ContentResultUpdate,
    ContentResultDelete,
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


@router.post(
    "/processed",
    response_model=PaginatedResponse,
    summary="Get all processed contents list",
    description="""
    Returns a list of all processed contents with pagination support.

    ## Parameters
    The parameter for pagination is passed in the request body as JSON.

    class Paging(BaseModel):
        page_number: int = Field(default=0, gt=0)
        page_size: int = Field(default=0, gt=0)

    The request body should contain the following fields:
    * **page_number** : The page number to retrieve (1-based index).
    * **page_size** : The number of items per page.
    * **page_number** and **page_size** are both required and must be greater than 0.

    ## Example Request Body
    {
        "page_number": 1,
        "page_size": 10
    }
    """,
)
async def get_all_processed_results(
    page_request: Paging,
    app_config: AppConfiguration = Depends(get_app_config),
) -> PaginatedResponse:
    # Get all the processed content
    paged_cosmos_content_process = CosmosContentProcess.get_all_processes_from_cosmos(
        connection_string=app_config.app_cosmos_connstr,
        database_name=app_config.app_cosmos_database,
        collection_name=app_config.app_cosmos_container_process,
        page_number=page_request.page_number if page_request else 0,
        page_size=page_request.page_size if page_request else 0,
    )

    return paged_cosmos_content_process


@router.post(
    "/submit",
    summary="Submit a file to be processed",
    description="""
    Submits a file to be processed by the content processor.
    the additional json payload should be passed with files.

    The file must be a PDF or image file (JPEG, BMP, GIF, PNG, TIFF) and should not exceed 20 MB in size.

    The request body should contain the following fields:
    - `Schema_Id`: The schema ID for the content processor.
    - `Metadata_Id`: The metadata ID for the content processor.

    ## Example Request Body
    {
        "Schema_Id": "registered schema id - UUID string",
        "Metadata_Id": "metadata_id"
    }

   """,
)
async def Submit_File_With_MetaData(
    data: ContentProcessorRequest = Body(...),
    file: UploadFile = File(...),
    content_processor: ContentProcessor = Depends(get_content_processor),
    app_config: AppConfiguration = Depends(get_app_config),
):
    # Save the uploaded file
    # 1. Check Mime Type and Validate whether file is supported - Should be pdf or image files
    if file.content_type not in [
        MimeTypes.Pdf,
        MimeTypes.ImageJpeg,
        MimeTypes.ImagePng,
        # MimeTypes.ImageBmp,
        # MimeTypes.ImageGif,
        # MimeTypes.ImageTiff,
    ]:
        return JSONResponse(
            status_code=415,
            content={
                "message": f"Unsupported file type: {file.content_type}. Only PDF and JPEG, PNG image files are available."
            },
        )

    # 2. Check File Size - Should be less than 20MB
    if file.size > app_config.app_cps_max_filesize_mb * 1024 * 1024:
        return JSONResponse(
            status_code=413,
            content={
                "message": f"File size exceeds the limit of {app_config.app_cps_max_filesize_mb} MB. Current size: {file.size / (1024 * 1024):.2f} MB."
            },
        )

    # Generate Process Id
    process_id = str(uuid.uuid4())

    # Save the file to Blob Storage
    content_processor.save_file_to_blob(
        process_id=process_id, file=file.file, file_name=file.filename
    )

    # Create Message Object to be sent to Queue
    submit_queue_message = ContentProcess(
        **{
            "process_id": process_id,
            "files": [
                ProcessFile(
                    **{
                        "process_id": process_id,
                        "id": str(uuid.uuid4()),
                        "name": file.filename,
                        "size": file.size,
                        "mime_type": file.content_type,
                        "artifact_type": ArtifactType.SourceContent,
                        "processed_by": "API",
                    }
                ),
            ],
            "pipeline_status": Status(
                **{
                    "process_id": process_id,
                    "schema_id": data.Schema_Id,
                    "metadata_id": data.Metadata_Id,
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
                }
            ),
        }
    )

    # Droop the message to Queue
    content_processor.enqueue_message(submit_queue_message)

    file_size_mb = file.size / (1024 * 1024)

    # Add Empty Process
    CosmosContentProcess(
        process_id=process_id,
        processed_file_name=file.filename,
        status="processing",
        imported_time=datetime.datetime.now(datetime.timezone.utc),
    ).update_process_status_to_cosmos(
        connection_string=content_processor.config.app_cosmos_connstr,
        database_name=content_processor.config.app_cosmos_database,
        collection_name=content_processor.config.app_cosmos_container_process,
    )
    return JSONResponse(
        status_code=202,
        content={
            "message": f"File '{file.filename}' of size {file_size_mb:.2f} MB received with metadata: {data} \n The file is being processed.",
            "status_url": f"/contentprocessor/status/{process_id}",
        },
    )


@router.get(
    "/status/{process_id}",
    summary="Get the status of a file being processing. it shows the status of the file being processed",
    description="""
            Returns the status of a file being processed by the content processor.

            Once the file is processed, the status will be updated to 'Completed' with return code 302.
            you can check the processed result by calling the endpoint '/contentprocessor/processed/{process_id}'.
            If the file processing fails, the status will be updated to 'Error' with return code 500.

            this method has been designed for aync processing of file processing.

            Once you file submitted for processing in /contentprocessor/submit, it will return a 202 status code with endpoint to check the status of the file.(/contentprocessor/status/{process_id}).
            Loop till you get the status code 302 or 500 with this endpoint.
            The status of the file can be one of the following:

            - `processing`: The file is being processed. - 200
            - `completed`: The file has been processed successfully. - 302
            - `failed`: the process id not found in process queue. - 404
            - `error`: The file processing has failed. - 500

            """,
)
async def get_status(
    process_id: str, app_config: AppConfiguration = Depends(get_app_config)
):
    # Get Content Process Status
    process_status = CosmosContentProcess(process_id=process_id).get_status_from_cosmos(
        connection_string=app_config.app_cosmos_connstr,
        database_name=app_config.app_cosmos_database,
        collection_name=app_config.app_cosmos_container_process,
    )

    if process_status is None:
        return JSONResponse(
            status_code=404,
            content={
                "status": "failed",
                "message": f"Processing of file with Process ID '{process_id}' not found.",
            },
        )

    if process_status.status == "Completed":
        return JSONResponse(
            status_code=302,
            content={
                "status": "completed",
                "message": f"Processing of file with Process ID '{process_id}' is completed.",
                "resource_url": f"/contentprocessor/processes/{process_id}",
            },
        )
    elif process_status == "Error":
        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "message": f"Processing of file with Process ID '{process_id}' has failed.",
            },
        )
    else:
        # Simulate a long-running process
        return JSONResponse(
            status_code=200,
            content={
                "status": process_status.status,
                "message": f"Processing of file with Process ID '{process_id}' is still in progress.",
            },
        )


@router.get(
    "/processed/{process_id}",
    response_model=CosmosContentProcess,
    summary="Get the processed content result",
    description="""
            Returns the processed content result for a given process ID.
            it returns whole processed content result with all the details in every step processing
            """,
)
async def get_process(
    process_id: str, app_config: AppConfiguration = Depends(get_app_config)
):
    # Get Content Process Status
    process_status = CosmosContentProcess(process_id=process_id).get_status_from_cosmos(
        connection_string=app_config.app_cosmos_connstr,
        database_name=app_config.app_cosmos_database,
        collection_name=app_config.app_cosmos_container_process,
    )

    if not process_status:
        return JSONResponse(
            status_code=404,
            content={
                "status": "failed",
                "message": f"Processing of file with Process ID '{process_id}' not found.",
            },
        )

    # process_status.process_output = CosmosContentProcess(
    #     process_id=process_id
    # ).get_status_from_blob(
    #     connection_string=app_config.app_storage_blob_url,
    #     blob_name="step_outputs.json",
    #     container_name=f"{app_config.app_cps_processes}/{process_status.process_id}",
    # )

    return process_status


@router.get(
    "/processed/{process_id}/steps",
    summary="Get the processed content results by step",
    description="""
            Some steps of the processing size is too large to be returned in the main processed content result.
            This endpoint returns only the processed content result for a given process ID.
            To reducing the payload of the processed content result in /processed/{process_id} endpoint,
            you may consider to call this  endpoint to reducing the payload of the processed content result.
            """,
)
async def get_process_steps(
    process_id: str, app_config: AppConfiguration = Depends(get_app_config)
):
    # Get Content Process Status
    process_steps = CosmosContentProcess(process_id=process_id).get_status_from_blob(
        connection_string=app_config.app_storage_blob_url,
        blob_name="step_outputs.json",
        container_name=f"{app_config.app_cps_processes}/{process_id}",
    )

    if not process_steps:
        return JSONResponse(
            status_code=404,
            content={
                "status": "failed",
                "message": f"Processing of file with Process ID '{process_id}' not found.",
            },
        )

    return process_steps


@router.put(
    "/processed/{process_id}",
    summary="Update the processed content result / Update the comment in this process",
    description="""
            Updates the processed content result for a given process ID.
            Updates the comment in the processed content result for a given process ID.

            It will be used for 2 purposes by the request payload:
            - Update the processed content result for a given process ID.
            - Update the comment in the processed content result for a given process ID.

            1. To Update the processed content result for a given process ID,
            payload with the following fields - ContentResultUpdate:
            - `process_id`: The process ID of the processed content.
            - `modified_result`: The modified result for the processed content. it should be a json object.
            ## Example Request Body

            {
                "process_id": "process_id",
                "modified_result": {
                    "key": "value"
                }
            }

            2. To Update the comment in the processed content result for a given process ID,
            payload with the following fields - ContentCommentUpdate:
            - `process_id`: The process ID of the processed content.
            - `comment`: The comment to be added to the processed content.
            ## Example Request Body
            {
                "process_id": "process_id",
                "comment": "This is a comment"
            }

            """,
)
async def update_process_result(
    process_id: str,
    content_update_request: ContentResultUpdate | ContentCommentUpdate,
    app_config: AppConfiguration = Depends(get_app_config),
):
    update_response: UpdateResult = None

    # Check paramter type - ContentResultUpdate or ContentCommentUpdate
    if isinstance(content_update_request, ContentResultUpdate):
        # Check if the request is of type ContentResultUpdate
        update_response = CosmosContentProcess(
            process_id=process_id,
        ).update_process_result(
            connection_string=app_config.app_cosmos_connstr,
            database_name=app_config.app_cosmos_database,
            collection_name=app_config.app_cosmos_container_process,
            process_result=content_update_request.modified_result,
        )

    if isinstance(content_update_request, ContentCommentUpdate):
        # Check if the request is of type ContentCommentUpdate
        update_response = CosmosContentProcess(
            process_id=process_id,
        ).update_process_comment(
            connection_string=app_config.app_cosmos_connstr,
            database_name=app_config.app_cosmos_database,
            collection_name=app_config.app_cosmos_container_process,
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
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"Processing of file with Process ID '{process_id}' updated.",
            },
        )


@router.get(
    "/processed/files/{process_id}",
    summary="Get the original file to be processed",
    description="""
            Returns the original file for a given process ID.
            it doesn't support file download but it supports file streaming to be used by the file viewer.
            The file will be returned as a streaming response with the appropriate content type.
            just use this endpoint for your file viewer URL.
            for example :
            contentviewer.url = http://<endpoint>/contentprocessor/processed/files/{process_id}
            """,
)
async def get_original_file(
    process_id: str, app_config: AppConfiguration = Depends(get_app_config)
):
    # Check processed content in Cosmos
    process_status = CosmosContentProcess(process_id=process_id).get_status_from_cosmos(
        connection_string=app_config.app_cosmos_connstr,
        database_name=app_config.app_cosmos_database,
        collection_name=app_config.app_cosmos_container_process,
    )

    if process_status is None:
        return JSONResponse(
            status_code=404,
            content={
                "status": "failed",
                "message": f"Processing of file with Process ID '{process_id}' not found.",
            },
        )

    # if not process_status: return 404
    if process_status is not None:
        # Get the file from Blob Storage
        file_bytes = process_status.get_file_bytes_from_blob(
            connection_string=app_config.app_storage_blob_url,
            blob_name=process_status.processed_file_name,
            container_name=f"{app_config.app_cps_processes}/{process_status.process_id}",
        )
        file_stream = io.BytesIO(file_bytes)

        # Encode the filename to support RFC 5987
        encoded_filename = urllib.parse.quote(process_status.processed_file_name)
        content_type_string = MimeTypesDetection.get_file_type(
            process_status.processed_file_name
        )
        # Set the response headers
        headers = {
            "Content-Disposition": f"inline; filename*=UTF-8''{encoded_filename}",
            "Content-Type": content_type_string,
        }

        return StreamingResponse(
            file_stream, media_type=content_type_string, headers=headers
        )


@router.delete(
    "/processed/{process_id}",
    response_model=ContentResultDelete,
    summary="Delete the processed content result",
    description="""
            Returns the deleted record for a given process ID.
            """,
)
async def delete_processed_file(
    process_id: str, app_config: AppConfiguration = Depends(get_app_config)
) -> ContentResultDelete:
    try:
        deleted_file = CosmosContentProcess(process_id=process_id).delete_processed_file(
            connection_string=app_config.app_cosmos_connstr,
            database_name=app_config.app_cosmos_database,
            collection_name=app_config.app_cosmos_container_process,
            storage_connection_string=app_config.app_storage_blob_url,
            container_name=app_config.app_cps_processes,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return ContentResultDelete(
        status="Success" if deleted_file else "Failed",
        process_id=deleted_file.process_id if deleted_file else "",
        message="" if deleted_file else "This record no longer exists. Please refresh."
    )
