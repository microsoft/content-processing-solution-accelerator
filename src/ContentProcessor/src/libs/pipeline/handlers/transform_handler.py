# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Transform handler — placeholder for custom data transformation logic.

Currently a pass-through step; extend ``execute()`` to add
post-extraction transformations before the save step.
"""

from libs.application.application_context import AppContext
from libs.pipeline.entities.pipeline_message_context import MessageContext
from libs.pipeline.entities.pipeline_step_result import StepResult
from libs.pipeline.queue_handler_base import HandlerBase


class TransformHandler(HandlerBase):
    """Pipeline step for custom data transformations (currently a no-op)."""

    def __init__(self, appContext: AppContext, step_name: str, **data):
        super().__init__(appContext, step_name, **data)

    async def execute(self, context: MessageContext) -> StepResult:
        print(context.data_pipeline.get_previous_step_result(self.handler_name))

        # TODO: Add transformation logic here

        return StepResult(
            process_id=context.data_pipeline.pipeline_status.process_id,
            step_name=self.handler_name,
            result={"result": "success"},
        )
