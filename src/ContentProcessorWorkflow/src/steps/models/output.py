# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Output models that flow through the claim-processing workflow.

Each executor appends an ``Executor_Output`` to the running
``Workflow_Output.workflow_process_outputs`` list, so downstream
steps can locate their predecessors' results by ``step_name``.
"""

from pydantic import BaseModel, Field


class Processed_Document_Info(BaseModel):
    """Summary record for a single processed document.

    Attributes:
        document_id: Unique identifier for the processed document.
        status:      Processing outcome (e.g. ``"processed"``, ``"failed"``).
        details:     Human-readable description of the outcome.
    """

    document_id: str = Field(description="Unique identifier for the processed document")
    status: str = Field(
        description="Processing status of the document (e.g., 'processed', 'failed')"
    )
    details: str = Field(description="Additional details about the processing outcome")


class Executor_Output(BaseModel):
    """Result payload produced by a single workflow executor.

    Attributes:
        step_name:   Identifier matching the executor's registration
                     name (e.g. ``"document_processing"``,
                     ``"summarizing"``, ``"gap_analysis"``).
        output_data: Free-form dictionary carrying the step's output.
    """

    step_name: str = Field(description="Name of the workflow step")
    output_data: dict = Field(description="Output data produced by the workflow step")


class Workflow_Output(BaseModel):
    """Accumulator that travels through every executor in the pipeline.

    Each executor reads the previous steps' results from
    ``workflow_process_outputs``, appends its own ``Executor_Output``,
    and forwards the updated object to the next step.

    Attributes:
        claim_process_id:        Batch identifier linking back to
                                 the Cosmos DB ``Claim_Process`` document.
        schemaset_id:            Schema set used for content extraction.
        workflow_process_outputs: Ordered list of per-step results.
    """

    claim_process_id: str = Field(
        description="Unique identifier for the claim processing"
    )
    schemaset_id: str = Field(
        description="Unique identifier for the schemaset used in processing"
    )
    workflow_process_outputs: list[Executor_Output] = Field(
        description="List of outputs from each workflow step",
        default_factory=lambda: [],
    )
