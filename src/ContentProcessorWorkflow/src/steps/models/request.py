# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Request models consumed by the claim-processing workflow.
"""

from pydantic import BaseModel, Field


class ClaimProcessTaskParameters(BaseModel):
    """Input parameters for a single claim-processing task.

    Attributes:
        claim_process_id: Unique batch identifier that the queue
            consumer passes into ``ClaimProcessor.run``.
    """

    claim_process_id: str = Field(
        description="Unique identifier for the claim batch processing"
    )
