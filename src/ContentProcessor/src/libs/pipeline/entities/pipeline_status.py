# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import datetime
from typing import List, Optional

from pydantic import Field

from libs.azure_helper.storage_blob import StorageBlobHelper
from libs.pipeline.entities.pipeline_message_base import PipelineMessageBase
from libs.pipeline.entities.pipeline_step_result import StepResult


class PipelineStatus(PipelineMessageBase):
    completed: bool = Field(default=False, alias="Completed")
    process_id: Optional[str] = Field(default=None, alias="ProcessId")
    metadata_id: Optional[str] = Field(default=None, alias="MetadataId")
    schema_id: Optional[str] = Field(default=None, alias="SchemaId")
    creation_time: Optional[str] = Field(default=None, alias="CreationTime")
    last_updated_time: Optional[str] = Field(default=None, alias="LastUpdateTime")
    active_step: Optional[str] = Field(default=None, alias="ActiveStep")
    steps: list[str] = Field(default_factory=list, alias="Steps")
    remaining_steps: list[str] = Field(default_factory=list, alias="RemainingSteps")
    completed_steps: list[str] = Field(default_factory=list, alias="CompletedSteps")
    process_results: Optional[List[StepResult]] = Field(
        default_factory=list, alias="ProcessResults"
    )

    def update_step(self):
        """
        Update the current active step in the pipeline.
        This method updates the `last_update_time` to the current UTC time
        and moves to the next step in the pipeline if there is an active step.
        """
        if self.active_step:
            # Set update time to pipeline status
            self.last_updated_time = datetime.datetime.now(
                datetime.timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

            self._move_to_next_step(self.active_step)

    def add_step_result(self, process_result: StepResult):
        """
        Add or update a StepResult in the process_results list.

        If a StepResult with the same step_name already exists, it will be updated.
        Otherwise, the new StepResult will be appended to the list.

        Args:
            process_result (StepResult): The StepResult object to add or update.
        """
        for i, existing_result in enumerate(self.process_results):
            if existing_result.step_name == process_result.step_name:
                # Update the existing StepResult
                self.process_results[i] = process_result
                return
        # If no match is found, append the new StepResult
        self.process_results.append(process_result)

    def get_step_result(self, step_name: str) -> Optional[StepResult]:
        """
        Get the StepResult for the given step_name

        Args:
            step_name (str): The name of the step to retrive the result for

        Returns:
            Optional[StepResult]: The StepResult for the given step_name. If no StepResult is found, return None
        """
        for result in self.process_results:
            if result.step_name == step_name:
                return result
        return None

    def get_previous_step_result(self, current_step_name: str) -> Optional[StepResult]:
        """
        Get the StepResult for the previous step in the pipeline.

        Args:
            step_name (str): The name of the current step

        Returns:
            Optional[StepResult]: The StepResult for the previous step in the pipeline. If no StepResult is found, return None
        """
        if len(self.completed_steps) == 0:
            return None

        previous_step = self.completed_steps[-1]
        return self.get_step_result(previous_step)

    def save_to_persistent_storage(self, account_url: str, container_name: str):
        # raise NotImplementedError
        """
        Save the current PipelineStatus to persistent storage.
        This method uploads the current status of the pipeline to a specified
        Azure Blob Storage account. The status is saved as a JSON file named
        "process-status.json" within a container named after the process ID.

        Args:
            account_url (str): The URL of the Azure Blob Storage account.

        Raises:
            ValueError: If the process ID is not set.
        """
        if self.process_id is None:
            raise ValueError("Process ID is required to save the result.")

        # Refresh the status
        self.update_step()

        StorageBlobHelper(
            account_url=account_url, container_name=container_name
        ).upload_text(
            container_name=self.process_id,
            blob_name="process-status.json",
            text=self.model_dump_json(),
        )

    def _move_to_next_step(self, step_name: str):
        """
        Update the status of the current step in the pipeline.
        Add the current step to the completed steps and remove it from the remaining steps.
        Update the LastUpdateTime to the current time.
        If there are no remaining steps, set the Completed flag to True.
        """
        # Add current step to the completed steps
        # Check if the step is already in the completed steps
        if step_name in self.completed_steps:
            self.last_updated_time = datetime.datetime.now(
                datetime.timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        self.completed_steps.append(step_name)
        # Remove current step from the remaining steps
        if step_name in self.remaining_steps:
            self.remaining_steps.remove(step_name)
        # If there are no remaining steps, set the Completed flag to True
        if len(self.remaining_steps) == 0:
            self.completed = True

    class Config:
        exclude_none = False
