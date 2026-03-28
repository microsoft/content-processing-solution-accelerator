# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Summarization executor for the claim workflow pipeline.

Second step in the three-stage pipeline (document_processing -> summarizing ->
gap_analysis).  Reads processed document extracts from the previous step,
runs a Summarization Agent to produce a consolidated summary, and persists the
result into Cosmos DB.
"""

from pathlib import Path
from typing import cast

from agent_framework import (
    ChatClientProtocol,
    ChatMessage,
    Executor,
    WorkflowContext,
    handler,
)

from libs.agent_framework.agent_builder import AgentBuilder
from libs.agent_framework.agent_framework_helper import AgentFrameworkHelper
from libs.application.application_context import AppContext
from repositories.claim_processes import Claim_Processes
from services.content_process_service import ContentProcessService
from steps.models.extracted_file import ExtractedFile
from steps.models.output import Executor_Output, Workflow_Output


class SummarizeExecutor(Executor):
    """Workflow executor that runs the summarization step.

    Responsibilities:
        1. Retrieve document-processing results from the previous executor.
        2. Fetch per-file extraction steps from the content-processing API.
        3. Build a list of ``ExtractedFile`` objects (PDF and image content).
        4. Load the summarization prompt and run the Summarization Agent.
        5. Persist the summary to the ``Claim_Process`` record in Cosmos DB.
        6. Forward the updated ``Workflow_Output`` to the next executor.

    Class-level Attributes:
        _PROMPT_FILE_NAME: Filename of the summarization prompt template.
    """

    _PROMPT_FILE_NAME = "summarize_executor_prompt.txt"

    def __init__(self, id: str, app_context: AppContext):
        """Create a new summarize executor bound to an application context."""
        super().__init__(id=id)
        self.app_context = app_context

    def _load_claim_summarization_prompt(self) -> str:
        """Load the summarization prompt template from disk.

        Returns:
            The prompt text with leading/trailing whitespace stripped.

        Raises:
            RuntimeError: If the prompt file is missing or empty.
        """
        prompt_path = (
            Path(__file__).resolve().parent.parent / "prompt" / self._PROMPT_FILE_NAME
        )
        try:
            prompt = prompt_path.read_text(encoding="utf-8")
        except FileNotFoundError as e:
            raise RuntimeError(
                f"Missing summarization prompt file: {prompt_path}. "
                "Expected file at src/steps/summarize/prompt/summarize_executor_prompt.txt"
            ) from e

        prompt = prompt.strip()
        if not prompt:
            raise RuntimeError(f"Summarization prompt file is empty: {prompt_path}")
        return prompt

    @handler
    async def handle_execute(
        self,
        result: Workflow_Output,
        ctx: WorkflowContext[Workflow_Output, Workflow_Output],
    ) -> None:
        """Execute summarization for a claim.

        Steps:
            1. Locate the ``document_processing`` output from the previous
               executor in the ``Workflow_Output``.
            2. For each successfully processed file (status 302), fetch the
               extraction steps from the content-processing API.
            3. Collect extracted markdown (PDFs) and mapped content (images)
               into ``ExtractedFile`` instances.
            4. Run the Summarization Agent over all extracted content.
            5. Persist the summary via ``Update_Claim_Process_Summary``.
            6. Append the summarization output and forward the result.

        Args:
            result: Workflow output accumulated by prior executors.
            ctx: Workflow context carrying shared state across executors.
        """
        previous_output = next(
            filter(
                lambda output: output.step_name == "document_processing",
                result.workflow_process_outputs,
            ),
            None,
        )
        document_results = (
            previous_output.output_data.get("document_results")
            if previous_output
            else None
        )

        if document_results is None:
            # If no document results found, return an error status
            summarized_result = {
                "status": "error",
                "message": "No document results to summarize.",
            }

            result.workflow_process_outputs.append(
                Executor_Output(step_name="summarizing", output_data=summarized_result)
            )

            await ctx.set_shared_state("workflow_output", result)
            await ctx.send_message(result)
            return

        processed_files: list[ExtractedFile] = []
        for document in document_results:
            if document["status"] != 302:
                continue  # Skip documents that were not processed successfully
            if document["mime_type"] == "application/pdf":
                process_id = document.get("process_id")
                processed_output = await self.fetch_processed_steps_result(process_id)
                if processed_output:
                    for step in processed_output:
                        if step["step_name"] == "extract":
                            extracted_file = ExtractedFile(
                                file_name=document["file_name"],
                                extracted_content=step["step_result"]["result"][
                                    "contents"
                                ][0]["markdown"],
                            )
                            processed_files.append(extracted_file)

            elif document["mime_type"] in ["image/png", "image/jpg", "image/jpeg"]:
                process_id = document.get("process_id")
                processed_output = await self.fetch_processed_steps_result(process_id)
                if processed_output:
                    for step in processed_output:
                        if (
                            step["step_name"] == "map"
                        ):  # Image files bypass the 'extract' step.
                            extracted_file = ExtractedFile(
                                file_name=document["file_name"],
                                mime_type=document["mime_type"],
                                extracted_content=step["step_result"]["choices"][0][
                                    "message"
                                ]["content"],
                            )
                            processed_files.append(extracted_file)

        agent_framework_helper = self.app_context.get_service(AgentFrameworkHelper)
        agent_client = await agent_framework_helper.get_client_async("default")

        if agent_client is None:
            raise RuntimeError("Chat client 'default' is not configured.")
        agent_client = cast(ChatClientProtocol, agent_client)

        claim_summarization_prompt = self._load_claim_summarization_prompt()

        agent = (
            AgentBuilder(agent_client)
            .with_name("Claim Summarization Agent")
            .with_instructions(claim_summarization_prompt)
            .with_temperature(0.1)
            .with_top_p(0.1)
            .build()
        )

        model_response = await agent.run(
            ChatMessage(
                role="user",
                text="Now summarize the following document extracts: : \n\n".join(
                    [
                        f"Document: {file.file_name}\nContent:\n{file.extracted_content}"
                        for file in processed_files
                    ]
                ),
            )
        )

        summarized_result = {"status": "summarized", "input": model_response.text}

        claim_process_repository = self.app_context.get_service(Claim_Processes)
        await claim_process_repository.Update_Claim_Process_Summary(
            process_id=result.claim_process_id, new_summary=model_response.text
        )
        result.workflow_process_outputs.append(
            Executor_Output(step_name="summarizing", output_data=summarized_result)
        )

        await ctx.set_shared_state("workflow_output", result)
        await ctx.send_message(result)

    async def fetch_processed_steps_result(self, process_id: str) -> dict | None:
        """Fetch the extraction steps for a processed document.

        Uses direct blob storage access instead of HTTP.

        Args:
            process_id: Content-processing process identifier.

        Returns:
            Parsed JSON list of step objects, or ``None`` if not found.
        """
        content_process_service = self.app_context.get_service(ContentProcessService)
        return await content_process_service.get_steps(process_id)
