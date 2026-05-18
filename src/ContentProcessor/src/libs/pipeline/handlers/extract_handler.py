# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Extract handler — document content extraction via Azure Content Understanding.

Processes PDF files through the Content Understanding pre-built layout
analyzer. Image files bypass extraction entirely.
"""

from libs.application.application_context import AppContext
from libs.azure_helper.content_understanding import AzureContentUnderstandingHelper
from libs.azure_helper.model.content_understanding import AnalyzedResult
from libs.pipeline.entities.mime_types import MimeTypes
from libs.pipeline.entities.pipeline_file import ArtifactType, PipelineLogEntry
from libs.pipeline.entities.pipeline_message_context import MessageContext
from libs.pipeline.entities.pipeline_step_result import StepResult
from libs.pipeline.queue_handler_base import HandlerBase


class ExtractHandler(HandlerBase):
    """Pipeline step that extracts structured content from source documents.

    Responsibilities:
        1. Route by MIME type (skip images, process PDFs).
        2. Invoke Azure Content Understanding for layout analysis.
        3. Persist extracted results to blob storage.
    """

    def __init__(self, appContext: AppContext, step_name: str, **data):
        super().__init__(appContext, step_name, **data)

    async def execute(self, context: MessageContext) -> StepResult:
        # if Content Type is image then skip extraction by Azure Content Understanding
        if context.data_pipeline.get_source_files()[0].mime_type in [
            MimeTypes.ImagePng,
            MimeTypes.ImageJpeg,
        ]:
            return StepResult(
                process_id=context.data_pipeline.pipeline_status.process_id,
                step_name=self.handler_name,
                result={
                    "result": "skipped",
                    "reason": "Content type is image, skipping extraction.",
                },
            )

        # if Content Type is PDF
        if context.data_pipeline.get_source_files()[0].mime_type == MimeTypes.Pdf:
            # Get File then pass it to Content Understanding Service
            async with self.application_context.create_scope() as scope:
                content_understanding_helper = scope.get_service(
                    AzureContentUnderstandingHelper
                )
                response = content_understanding_helper.begin_analyze_stream(
                    analyzer_id="prebuilt-layout",
                    file_stream=context.data_pipeline.get_source_files()[
                        0
                    ].download_stream(
                        self.application_context.configuration.app_storage_blob_url,
                        self.application_context.configuration.app_cps_processes,
                    ),
                )

                response = content_understanding_helper.poll_result(response)
                result: AnalyzedResult = AnalyzedResult(**response)

            # Save Result as a file
            # Create File Entity to add
            result_file = context.data_pipeline.add_file(
                file_name="content_understanding_output.json",
                artifact_type=ArtifactType.ExtractedContent,
            )

            # log for file uploading
            result_file.log_entries.append(
                PipelineLogEntry(**{
                    "source": self.handler_name,
                    "message": "Content Understanding Extraction Result has been added",
                })
            )

            # Upload the result to blob storage
            result_file.upload_json_text(
                account_url=self.application_context.configuration.app_storage_blob_url,
                container_name=self.application_context.configuration.app_cps_processes,
                text=result.model_dump_json(),
            )

            return StepResult(
                process_id=context.data_pipeline.pipeline_status.process_id,
                step_name=self.handler_name,
                result={
                    "result": "success",
                    "file_name": result_file.name,
                },
            )

        # Fallback for unsupported content types
        return StepResult(
            process_id=context.data_pipeline.pipeline_status.process_id,
            step_name=self.handler_name,
            result={
                "result": "skipped",
                "reason": "Content type not supported for extraction.",
            },
        )
