# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Pipeline step navigation helper.

Provides lookup logic to determine the next step in the ordered
pipeline sequence given the current step.
"""

from typing import Optional

from libs.pipeline.entities.pipeline_status import PipelineStatus


def get_next_step_name(
    status: PipelineStatus, current_step: Optional[str] = None
) -> str:
    """Return the name of the step after the active step, or None if last."""
    next_index = status.steps.index(status.active_step) + 1
    if next_index < len(status.steps):
        return status.steps[next_index]
    else:
        return None
