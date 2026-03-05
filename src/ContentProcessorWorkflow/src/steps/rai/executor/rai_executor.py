# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Responsible-AI safety gate for the claim-processing workflow.

This executor sits between the document-extraction step and the
summarisation step.  It sends extracted text to an LLM-based safety
classifier and blocks the pipeline when the content is deemed unsafe.
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
from steps.models.extracted_file import ExtractedFile
from steps.models.output import Executor_Output, Workflow_Output
from steps.rai.model import rai_response
from utils.http_request import HttpRequestClient


class RAIExecutor(Executor):
    """Workflow executor that applies Responsible-AI content analysis.

    Responsibilities:
        1. Collect extracted text from the document-processing step.
        2. Send the concatenated text to an LLM safety classifier.
        3. Block the workflow if the content is flagged as unsafe.

    Attributes:
        app_context: Shared application context for service resolution.
    """

    _PROMPT_FILE_NAME = "rai_executor_prompt.txt"

    def __init__(self, id: str, app_context: AppContext):
        super().__init__(id=id)
        self.app_context = app_context

    def _load_rai_executor_prompt(self) -> str:
        """Load the RAI executor prompt template from disk.

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
                f"Missing RAI executor prompt file: {prompt_path}. "
                "Expected file at src/steps/rai/prompt/rai_executor_prompt.txt"
            ) from e

        prompt = prompt.strip()
        if not prompt:
            raise RuntimeError(f"RAI executor prompt file is empty: {prompt_path}")
        return prompt

    @handler
    async def handle_exectue(
        self,
        result: Workflow_Output,
        ctx: WorkflowContext[Workflow_Output, Workflow_Output],
    ) -> None:

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
            rai_result = {
                "status": "error",
                "message": "No document results to analyze RAI.",
            }

            result.workflow_process_outputs.append(
                Executor_Output(step_name="rai_analysis", output_data=rai_result)
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
                        # Image files bypass the 'extract' step.
                        if step["step_name"] == "map":
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

        rai_executor_prompt = self._load_rai_executor_prompt()

        agent = (
            AgentBuilder(agent_client)
            .with_name("RAI Agent")
            .with_temperature(0.1)
            .with_instructions(rai_executor_prompt)
            .with_response_format(rai_response.RAIResponse)
            .build()
        )

        document_text = "\n\n---\n\n".join(
            f"Document: {file.file_name}\nContent:\n{file.extracted_content}"
            for file in processed_files
        )

        print(f"[For Debuggging]:\n{document_text}\n[/For Debuggging]")

        model_response = await agent.run(
            ChatMessage(
                role="user",
                text=document_text,
            )
        )

        response_content = model_response.text
        parsed_response = rai_response.RAIResponse.model_validate_json(response_content)

        if parsed_response.IsNotSafe:
            raise RuntimeError("Content is considered unsafe by RAI analysis.")

        await ctx.send_message(result)

    async def fetch_processed_steps_result(self, process_id: str) -> dict | None:
        """Fetch the extraction steps for a processed document.

        Args:
            process_id: Content-processing process identifier.

        Returns:
            Parsed JSON list of step objects, or ``None`` on non-200 responses.
        """
        base_endpoint = (
            self.app_context.configuration.app_cps_content_process_endpoint or ""
        ).rstrip("/")

        fetch_processed_result_path = (
            "/submit"
            if base_endpoint.endswith("/contentprocessor")
            else "/contentprocessor/processed"
        )

        async with HttpRequestClient() as http_client:
            url = f"{base_endpoint}{fetch_processed_result_path}/{process_id}/steps"
            response = await http_client.get(url)
            if response.status == 200:
                return response.json()
            else:
                return None
