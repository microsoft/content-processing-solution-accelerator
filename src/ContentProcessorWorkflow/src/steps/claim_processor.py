# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Claim-processing workflow orchestration.

This module wires together the end-to-end claim-processing pipeline
executed by the queue consumer.

``ClaimProcessor`` builds an ``agent_framework.Workflow``, streams its
events to track executor progress, and surfaces failures as rich
exceptions that preserve the framework's ``WorkflowErrorDetails``
payload.

Pipeline order:
    ``document_processing`` -> [``rai_analysis``] -> ``summarizing`` -> ``gap_analysis``

    The ``rai_analysis`` step is conditional on
    ``AppConfiguration.app_rai_enabled``.  When disabled, the workflow
    skips directly from document processing to summarising.

Key behaviours:
    * Each executor invocation updates the ``Claim_Process`` status in
      Cosmos DB so the API layer can report real-time progress.
    * On failure the status is set to ``FAILED`` and the error message
      is persisted in ``process_comment``.
    * Elapsed wall-clock time is recorded in ``processed_time`` once
      the pipeline finishes (success or failure).
"""

import json
import logging
import time
from datetime import datetime
from typing import Any

from agent_framework import (
    ExecutorCompletedEvent,
    ExecutorFailedEvent,
    ExecutorInvokedEvent,
    Workflow,
    WorkflowBuilder,
    WorkflowFailedEvent,
    WorkflowOutputEvent,
    WorkflowStartedEvent,
)
from art import text2art

from libs.application.application_context import AppContext
from repositories.claim_processes import Claim_Processes
from repositories.model.claim_process import Claim_Steps

from .document_process.executor.document_process_executor import DocumentProcessExecutor
from .gap_analysis.executor.gap_executor import GapExecutor
from .rai.executor.rai_executor import RAIExecutor
from .summarize.executor.summarize_executor import SummarizeExecutor

logger = logging.getLogger(__name__)


class WorkflowExecutorFailedException(Exception):
    """Raised when an executor fails, preserving WorkflowErrorDetails payload."""

    def __init__(self, details: Any):
        self.details = details
        super().__init__(self._format_message(details))

    @staticmethod
    def _details_to_dict(details: Any) -> dict[str, Any]:
        if details is None:
            return {"details": None}

        if isinstance(details, dict):
            return details

        # Pydantic v2
        model_dump = getattr(details, "model_dump", None)
        if callable(model_dump):
            try:
                dumped = model_dump()
                if isinstance(dumped, dict):
                    return dumped
                return {"details": dumped}
            except Exception:
                pass

        # Generic objects / dataclasses
        try:
            return dict(vars(details))
        except Exception:
            return {"details": repr(details)}

    @classmethod
    def _format_message(cls, details: Any) -> str:
        payload = cls._details_to_dict(details)
        executor_id = payload.get("executor_id", "<unknown>")
        error_type = payload.get("error_type", "<unknown>")
        message = payload.get("message", "<no message>")
        traceback = payload.get("traceback")

        payload_json = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
        if traceback:
            return (
                f"Executor {executor_id} failed ({error_type}): {message}\n"
                f"WorkflowErrorDetails:\n{payload_json}\n"
                f"Traceback:\n{traceback}"
            )
        return (
            f"Executor {executor_id} failed ({error_type}): {message}\n"
            f"WorkflowErrorDetails:\n{payload_json}"
        )


class WorkflowOutputMissingException(Exception):
    """Raised when the workflow completes without producing a usable output."""

    def __init__(self, source_executor_id: str | None):
        self.source_executor_id = source_executor_id
        super().__init__(
            f"Workflow output is None (source_executor_id={source_executor_id or '<unknown>'})"
        )


class ClaimProcessor:
    """Orchestrates the claim processing workflow and reports progress.

    The processor is responsible for:

    - Building the workflow graph (executor registration + edges).
    - Executing the workflow as an async event stream.
    - Emitting console output for progress and failures.

    Parameters
    ----------
    app_context:
        Application DI container used to resolve services.
    """

    def __init__(self, app_context: AppContext):
        self.app_context = app_context
        self.workflow = self._init_workflow()

    def _init_workflow(self) -> Workflow:
        """Create and return the configured workflow instance.

        The workflow is a conditional pipeline:

        ``Document Processing`` → [``RAI Analysis``] → ``Summarizing`` → ``GAP Analysis``

        The RAI analysis step is included only when
        ``app_context.configuration.app_rai_enabled`` is ``True``.

        Returns
        -------
        Workflow
            The built workflow ready to execute.
        """

        workflow = (
            WorkflowBuilder()
            .register_executor(
                lambda: DocumentProcessExecutor(
                    id="document_processing", app_context=self.app_context
                ),
                name="document_processing",
            )
            .register_executor(
                lambda: RAIExecutor(id="rai_analysis", app_context=self.app_context),
                name="rai_analysis",
            )
            .register_executor(
                lambda: SummarizeExecutor(
                    id="summarizing", app_context=self.app_context
                ),
                name="summarizing",
            )
            .register_executor(
                lambda: GapExecutor(id="gap_analysis", app_context=self.app_context),
                name="gap_analysis",
            )
            .set_start_executor("document_processing")
            # Edges define the execution flow and can include conditions for branching logic.
            # In this case, we conditionally branch to the RAI analysis step based on the
            # application configuration, allowing it to be toggled on/off without code changes.
            .add_edge(
                source="document_processing",
                target="rai_analysis",
                condition=lambda _: self.app_context.configuration.app_rai_enabled,
            )
            .add_edge(source="rai_analysis", target="summarizing")
            # If RAI analysis is disabled, the summarizing step will execute immediately after document processing
            .add_edge(
                source="document_processing",
                target="summarizing",
                condition=lambda _: not self.app_context.configuration.app_rai_enabled,
            )
            .add_edge(source="summarizing", target="gap_analysis")
            .build()
        )

        return workflow

    async def run(self, input_data: str) -> Any:
        """Run the migration workflow.

        The workflow is executed via ``run_stream`` and handled as a sequence of
        framework events. This method:

        - Captures a structured report summary for success/failure outcomes.
        - Returns the final workflow output.

        Parameters
        ----------
        input_data:
            Input parameters for the analysis step. The same object is propagated
            through the workflow and is expected to include a ``process_id``.

        Returns
        -------
        Any
            The final workflow output. If the workflow hard-terminates, the returned
            object represents the hard-termination payload so upstream callers can
            display blockers.

        Raises
        ------
        WorkflowExecutorFailedException
            If any executor fails or if the workflow produces no output.
        """
        start_dt = datetime.now()
        start_perf = time.perf_counter()

        last_failed_executor_id: str | None = None
        last_invoked_executor_id: str | None = None

        try:
            async for event in self.workflow.run_stream(input_data):
                if isinstance(event, WorkflowStartedEvent):
                    logger.info("Workflow started (%s)", event.origin.value)
                elif isinstance(event, WorkflowOutputEvent):
                    claim_process_repository = self.app_context.get_service(
                        Claim_Processes
                    )
                    await claim_process_repository.Update_Claim_Process_Status(
                        process_id=input_data, new_status=Claim_Steps.COMPLETED
                    )
                    return event.data
                elif isinstance(event, ExecutorFailedEvent):
                    last_failed_executor_id = event.executor_id
                elif isinstance(event, WorkflowFailedEvent):
                    batch_id = input_data
                    executor_id = (
                        event.details.executor_id
                        or last_failed_executor_id
                        or last_invoked_executor_id
                        or "<unknown>"
                    )
                    claim_process_repository = self.app_context.get_service(
                        Claim_Processes
                    )
                    await claim_process_repository.Update_Claim_Process_Status(
                        process_id=batch_id, new_status=Claim_Steps.FAILED
                    )
                    await claim_process_repository.Update_Claim_Process_Comment(
                        process_id=batch_id,
                        new_comment=f"Workflow failed at executor {executor_id}: {event.details.message}",
                    )
                    raise WorkflowExecutorFailedException(event.details)

                elif isinstance(event, ExecutorInvokedEvent):
                    last_invoked_executor_id = event.executor_id
                    logger.info("\n%s", text2art(event.executor_id.capitalize()))
                    claim_process_repository = self.app_context.get_service(
                        Claim_Processes
                    )
                    if event.executor_id == "document_processing":
                        new_status = Claim_Steps.DOCUMENT_PROCESSING
                    elif event.executor_id == "summarizing":
                        new_status = Claim_Steps.SUMMARIZING
                    elif event.executor_id == "gap_analysis":
                        new_status = Claim_Steps.GAP_ANALYSIS
                    elif event.executor_id == "rai_analysis":
                        new_status = Claim_Steps.RAI_ANALYSIS
                    else:
                        new_status = None

                    if new_status is not None:
                        await claim_process_repository.Update_Claim_Process_Status(
                            process_id=input_data, new_status=new_status
                        )
                elif isinstance(event, ExecutorCompletedEvent):
                    pass
                else:
                    pass

            # Stream exhausted without a WorkflowOutputEvent or WorkflowFailedEvent
            raise WorkflowOutputMissingException(last_invoked_executor_id)
        finally:
            elapsed_seconds = time.perf_counter() - start_perf
            end_dt = datetime.now()
            total_ms = int(round(elapsed_seconds * 1000.0))
            total_secs, ms = divmod(total_ms, 1000)
            mins, secs = divmod(total_secs, 60)
            hours, mins = divmod(mins, 60)
            elapsed_formatted = f"{hours:02d}:{mins:02d}:{secs:02d}.{ms:02d}"
            logger.info(
                "Workflow elapsed time: %s (start=%s, end=%s)",
                elapsed_formatted,
                start_dt.isoformat(timespec="seconds"),
                end_dt.isoformat(timespec="seconds"),
            )

            claim_process_repository = self.app_context.get_service(Claim_Processes)
            claim_process = await claim_process_repository.get_async(input_data)
            if claim_process:
                claim_process.processed_time = elapsed_formatted
                await claim_process_repository.update_async(claim_process)
