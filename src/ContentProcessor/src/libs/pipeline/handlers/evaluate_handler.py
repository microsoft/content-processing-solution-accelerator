# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Evaluate handler — confidence scoring for extracted data.

Merges confidence signals from Azure Content Understanding OCR and
OpenAI logprobs to produce per-field and overall confidence scores.
"""

import json

from libs.application.application_context import AppContext
from libs.azure_helper.model.content_understanding import AnalyzedResult
from libs.pipeline.entities.mime_types import MimeTypes
from libs.pipeline.entities.pipeline_file import ArtifactType, PipelineLogEntry
from libs.pipeline.entities.pipeline_message_context import MessageContext
from libs.pipeline.entities.pipeline_step_result import StepResult
from libs.pipeline.handlers.logics.evaluate_handler.comparison import (
    get_extraction_comparison_data,
)
from libs.pipeline.handlers.logics.evaluate_handler.confidence import (
    merge_confidence_values,
)
from libs.pipeline.handlers.logics.evaluate_handler.content_understanding_confidence_evaluator import (
    evaluate_confidence as content_understanding_confidence,
)
from libs.pipeline.handlers.logics.evaluate_handler.model import DataExtractionResult
from libs.pipeline.handlers.logics.evaluate_handler.openai_confidence_evaluator import (
    evaluate_confidence as gpt_confidence,
)
from libs.pipeline.queue_handler_base import HandlerBase


class EvaluateHandler(HandlerBase):
    """Pipeline step that scores extraction confidence.

    Responsibilities:
        1. Retrieve results from the extract and map steps.
        2. Compute confidence from Content Understanding and GPT logprobs.
        3. Merge scores and produce field-level comparison data.
    """

    def __init__(self, appContext: AppContext, step_name: str, **data):
        super().__init__(appContext, step_name, **data)

    async def execute(self, context: MessageContext) -> StepResult:
        source_mime_type = context.data_pipeline.get_source_files()[0].mime_type
        content_understanding_result: AnalyzedResult | None = None

        # Get the result from Extract step handler only for non-image content types
        if source_mime_type not in [MimeTypes.ImageJpeg, MimeTypes.ImagePng]:
            # Get the result from Extract step
            output_file_json_string_from_extract = (
                self.download_output_file_to_json_string(
                    processed_by="extract",
                    artifact_type=ArtifactType.ExtractedContent,
                )
            )
            if output_file_json_string_from_extract:
                # Deserialize the result to AnalyzedResult (Content Understanding)
                content_understanding_result = AnalyzedResult(
                    **json.loads(output_file_json_string_from_extract)
                )

        # Get the result from Map step handler - Azure AI Foundry
        output_file_json_string_from_map = self.download_output_file_to_json_string(
            processed_by="map",
            artifact_type=ArtifactType.SchemaMappedData,
        )

        # Deserialize the result from Map step to dict
        gpt_result = json.loads(output_file_json_string_from_map)

        # Mapped Result from Azure AI Foundry
        parsed_message_from_gpt = gpt_result["choices"][0]["message"]["parsed"]

        # Convert the parsed message to a dictionary
        gpt_evaluate_confidence_dict = parsed_message_from_gpt

        # Evaluate Confidence Score - Content Understanding
        content_understanding_confidence_score = None
        if content_understanding_result is not None:
            content_understanding_confidence_score = content_understanding_confidence(
                gpt_evaluate_confidence_dict,
                content_understanding_result.result.contents[0],
            )

        # Evaluate Confidence Score - GPT
        gpt_confidence_score = gpt_confidence(
            gpt_evaluate_confidence_dict, gpt_result["choices"][0]
        )

        # Merge the confidence scores - Content Understanding and GPT results.
        if content_understanding_confidence_score is None:
            # For images (or missing extract output), compute summary stats from GPT confidence only.
            merged_confidence_score = merge_confidence_values(
                gpt_confidence_score, gpt_confidence_score
            )
        else:
            merged_confidence_score = merge_confidence_values(
                content_understanding_confidence_score, gpt_confidence_score
            )

        # Flatten extracted data and confidence score
        result_data = get_extraction_comparison_data(
            actual=gpt_evaluate_confidence_dict,
            confidence=merged_confidence_score,
            threads_hold=0.8,  # TODO: Get this from config
        )

        # Put all results in a single object
        all_results = DataExtractionResult(
            extracted_result=gpt_evaluate_confidence_dict,
            confidence=merged_confidence_score,
            comparison_result=result_data,
            prompt_tokens=gpt_result["usage"]["prompt_tokens"],
            completion_tokens=gpt_result["usage"]["completion_tokens"],
            execution_time=0,
        )

        # Save Result as a file
        result_file = context.data_pipeline.add_file(
            file_name="evaluate_output.json",
            artifact_type=ArtifactType.ScoreMergedData,
        )
        result_file.log_entries.append(
            PipelineLogEntry(**{
                "source": self.handler_name,
                "message": "Evaluation Result has been added",
            })
        )
        result_file.upload_json_text(
            account_url=self.application_context.configuration.app_storage_blob_url,
            container_name=self.application_context.configuration.app_cps_processes,
            text=all_results.model_dump_json(),
        )

        return StepResult(
            process_id=context.data_pipeline.pipeline_status.process_id,
            step_name=self.handler_name,
            result={"result": "success", "file_name": result_file.name},
        )
