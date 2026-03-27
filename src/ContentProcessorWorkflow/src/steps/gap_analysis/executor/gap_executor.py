# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""GAP-analysis executor for the claim workflow pipeline.

Third and final step in the three-stage pipeline (document_processing ->
summarizing -> gap_analysis).  Reads processed document extracts from the
first step, loads a prompt template and YAML rules file, runs a GAP Analysis
Agent to identify missing or incomplete information, and persists the gaps
into Cosmos DB.
"""

import json
from datetime import date, datetime, time
from pathlib import Path
from typing import Never, cast

import yaml
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


class GapExecutor(Executor):
    """Workflow executor that runs the GAP-analysis step.

    Responsibilities:
        1. Retrieve document-processing results from the first executor.
        2. Fetch the full processed output (JSON) for each document.
        3. Load the prompt template and YAML rules, injecting rules into
           the ``{{RULES_DSL}}`` placeholder.
        4. Run the GAP Analysis Agent over all extracted content.
        5. Persist the identified gaps to the ``Claim_Process`` record.
        6. Yield the final ``Workflow_Output`` to conclude the pipeline.

    Class-level Attributes:
        _PROMPT_FILE_NAME: Filename of the GAP-analysis prompt template.
        _RULES_FILE_NAME: Filename of the YAML rules DSL.
    """

    _PROMPT_FILE_NAME = "gap_executor_prompt.txt"
    _RULES_FILE_NAME = "fnol_gap_rules.dsl.yaml"

    def __init__(self, id: str, app_context: AppContext):
        """Create a new GAP executor bound to an application context."""
        super().__init__(id=id)
        self.app_context = app_context

    def _read_text_file(self, path: Path) -> str:
        """Read and return the stripped contents of a text file.

        Raises:
            RuntimeError: If the file is empty after stripping.
        """
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            raise RuntimeError(f"Required prompt/rules file is empty: {path}")
        return text

    def _load_prompt_and_rules(self) -> str:
        """Load the prompt template and inject the YAML rules DSL.

        Returns:
            The prompt string with ``{{RULES_DSL}}`` replaced by the rules.

        Raises:
            RuntimeError: If either file is missing/empty or rules YAML is
                invalid.
        """
        gap_dir = Path(__file__).resolve().parent.parent
        prompt_path = gap_dir / "prompt" / self._PROMPT_FILE_NAME
        rules_path = gap_dir / "prompt" / self._RULES_FILE_NAME

        prompt_template = self._read_text_file(prompt_path)
        rules_text = self._read_text_file(rules_path)

        # Validate rules YAML early so failures are clear and actionable.
        try:
            yaml.safe_load(rules_text)
        except Exception as e:
            raise RuntimeError(f"Invalid YAML in rules file: {rules_path}") from e

        return prompt_template.replace("{{RULES_DSL}}", rules_text)

    def _json_default(self, value: object) -> str:
        """Convert non-JSON-native values from processed output into strings."""
        if isinstance(value, (datetime, date, time)):
            return value.isoformat()
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")

    def _serialize_processed_output(self, processed_output: dict) -> str:
        """Serialize processed output for prompt injection.

        Content-processing results can contain Python datetime objects when they
        are materialized from storage, so serialize those explicitly instead of
        letting ``json.dumps`` fail mid-workflow.
        """
        return json.dumps(
            processed_output,
            ensure_ascii=False,
            default=self._json_default,
        )

    @handler
    async def handle_execute(
        self,
        result: Workflow_Output,
        ctx: WorkflowContext[Never, Workflow_Output],
    ) -> None:
        """Execute GAP analysis for a claim.

        Steps:
            1. Locate the ``document_processing`` output from the first
               executor in the ``Workflow_Output``.
            2. For each successfully processed document (status 302), fetch
               the full processed result as JSON.
            3. Build ``ExtractedFile`` instances with the serialised JSON.
            4. Load the GAP-analysis prompt (with rules injected) and run
               the GAP Analysis Agent.
            5. Persist the identified gaps via ``Update_Claim_Process_Gaps``.
            6. Append the GAP output and yield the final result.

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
            gap_analysis_summary = {
                "status": "error",
                "message": "No document results to analyze gaps.",
            }

            result.workflow_process_outputs.append(
                Executor_Output(
                    step_name="gap_analysis", output_data=gap_analysis_summary
                )
            )

            await ctx.set_shared_state("workflow_output", result)
            await ctx.yield_output(result)
            return

        processed_files: list[ExtractedFile] = []

        for document in document_results:
            if document["status"] != 302:
                continue  # Skip documents that were not processed successfully
            process_id = document.get("process_id")
            processed_output = await self.fetch_processed_result(process_id)
            if processed_output:
                extracted_file = ExtractedFile(
                    file_name=document["file_name"],
                    mime_type=document["mime_type"],
                    extracted_content=self._serialize_processed_output(processed_output),
                )
                processed_files.append(extracted_file)

        agent_framework_helper = self.app_context.get_service(AgentFrameworkHelper)
        agent_client = await agent_framework_helper.get_client_async("default")

        if agent_client is None:
            raise RuntimeError("Chat client 'default' is not configured.")
        agent_client = cast(ChatClientProtocol, agent_client)

        claim_gap_analysis_prompt = self._load_prompt_and_rules()

        agent = (
            AgentBuilder(agent_client)
            .with_name("GAP Analysis Agent")
            .with_instructions(claim_gap_analysis_prompt)
            .with_temperature(0.1)
            .with_top_p(0.1)
            .build()
        )

        model_response = await agent.run(
            ChatMessage(
                role="user",
                text="Now analyze the following document extracts:\n\n"
                + "\n\n".join([
                    f"Document: {file.file_name} ({file.mime_type})\nExtracted Values with Schema (JSON):\n{file.extracted_content}"
                    for file in processed_files
                ]),
            )
        )

        claim_process_repository = self.app_context.get_service(Claim_Processes)
        await claim_process_repository.Update_Claim_Process_Gaps(
            process_id=result.claim_process_id, new_gaps=model_response.text
        )

        gap_result = {"status": "gap_processed", "output": model_response.text}

        result.workflow_process_outputs.append(
            Executor_Output(step_name="gap_analysis", output_data=gap_result)
        )

        await ctx.set_shared_state("workflow_output", result)
        await ctx.yield_output(result)

    async def fetch_processed_result(self, process_id: str) -> dict | None:
        """Fetch the full processed output for a document.

        Uses direct Cosmos DB access instead of HTTP.

        Args:
            process_id: Content-processing process identifier.

        Returns:
            Parsed JSON object, or ``None`` if not found.
        """
        content_process_service = self.app_context.get_service(ContentProcessService)
        return await content_process_service.get_processed(process_id)
