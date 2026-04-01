# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Abstract base class for queue-driven pipeline handlers.

Defines the message-processing loop, error handling, dead-letter routing,
and persistence lifecycle that all concrete step handlers inherit.
"""

import asyncio
import base64
import datetime
import json
import logging
from abc import ABC, abstractmethod

from azure.storage.queue import QueueClient
from libs.application.application_context import AppContext
from libs.base.application_models import AppModelBase
from libs.models.content_process import ContentProcess, Step_Outputs
from libs.pipeline import pipeline_queue_helper
from libs.pipeline.entities.pipeline_data import DataPipeline
from libs.pipeline.entities.pipeline_file import ArtifactType, PipelineLogEntry
from libs.pipeline.entities.pipeline_message_context import MessageContext
from libs.pipeline.entities.pipeline_step_result import StepResult
from libs.utils import base64_util, stopwatch


class HandlerBase(AppModelBase, ABC):
    """Abstract queue handler implementing the processing loop.

    Responsibilities:
        1. Connect to an Azure Storage Queue and poll for messages.
        2. Deserialize messages into ``DataPipeline`` payloads.
        3. Delegate to the concrete ``execute()`` method.
        4. Persist results, advance the pipeline, and handle errors.

    Attributes:
        handler_name: Pipeline step name (e.g. 'extract', 'map').
        queue_client: Azure Storage Queue client for the step.
        application_context: Shared application context / DI container.
    """

    handler_name: str = None
    queue_client: QueueClient = None
    queue_name: str = None
    application_context: AppContext = None
    dead_letter_queue_client: QueueClient = None
    dead_letter_queue_name: str = None
    _current_message_context: MessageContext = None

    def __init__(self, appContext: AppContext, step_name: str, **data):
        super().__init__(**data)

    async def _connect_async(
        self,
        show_information: bool = True,
        app_context: AppContext = None,
        step_name: str = None,
    ):
        # Initialize the handler
        self.__initialize_handler(app_context, step_name)

        while True:
            checking_message: str = """Checking Message.... at {datetime} by {queue_name}
            """
            checking_message = checking_message.format(
                # UTC time
                datetime=datetime.datetime.now(datetime.UTC).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                queue_name=self.queue_name,
            )

            logging.info(checking_message) if show_information else None

            # Check if queue is available in the storage account or not
            pipeline_queue_helper.invalidate_queue(self.queue_client)
            pipeline_queue_helper.invalidate_queue(self.dead_letter_queue_client)

            # Check if there are any messages in the queue
            if not pipeline_queue_helper.has_messages(self.queue_client):
                print(
                    f"No messages found. - {self.queue_name}"
                ) if show_information else None

                await asyncio.sleep(
                    # Sleep for 5 seconds
                    self.application_context.configuration.app_message_queue_interval
                )
                continue

            # Process the message
            for queue_message in self.queue_client.receive_messages(
                max_messages=1,
                visibility_timeout=self.application_context.configuration.app_message_queue_process_timeout,
            ):
                logging.info(
                    f"Message dequeued {self.queue_name}: {queue_message.content}"
                ) if show_information else None

                # Check if the message content is Base64 encoded string
                if base64_util.is_base64_encoded(queue_message.content):
                    queue_message.content = base64.b64decode(
                        queue_message.content
                    ).decode("utf-8")

                data_pipeline: DataPipeline = DataPipeline.get_object(
                    queue_message.content
                )

                try:
                    if data_pipeline is not None:
                        print(
                            f"Message received: {self.handler_name} \n {data_pipeline}"
                        ) if show_information else None

                        self._current_message_context = MessageContext(
                            queue_message=queue_message,
                            data_pipeline=data_pipeline,
                        )

                        self._current_message_context.data_pipeline.pipeline_status.active_step = self.handler_name

                        # Update status to the currently running step BEFORE execution
                        # so the UI reflects real-time progress.
                        ContentProcess(
                            process_id=self._current_message_context.data_pipeline.pipeline_status.process_id,
                            processed_file_name=self._current_message_context.data_pipeline.files[
                                0
                            ].name,
                            processed_file_mime_type=self._current_message_context.data_pipeline.files[
                                0
                            ].mime_type,
                            status=step_name,
                            imported_time=datetime.datetime.strptime(
                                self._current_message_context.data_pipeline.pipeline_status.creation_time,
                                "%Y-%m-%dT%H:%M:%S.%fZ",
                            ),
                            last_modified_time=datetime.datetime.now(datetime.UTC),
                            last_modified_by=step_name,
                        ).update_process_status_to_cosmos(
                            connection_string=self.application_context.configuration.app_cosmos_connstr,
                            database_name=self.application_context.configuration.app_cosmos_database,
                            collection_name=self.application_context.configuration.app_cosmos_container_process,
                        )

                        print(
                            f"Start Processing : {self.handler_name}"
                        ) if show_information else None
                        with stopwatch.Stopwatch() as timer:
                            step_result = await self.execute(
                                self._current_message_context
                            )
                        print(
                            f"Completed : {self.handler_name} - Elapsed :{timer.elapsed_string}"
                        ) if show_information else None
                        step_result.elapsed = timer.elapsed_string

                        step_result.save_to_persistent_storage(
                            self.application_context.configuration.app_storage_blob_url,
                            self.application_context.configuration.app_cps_processes,
                        )

                        self._current_message_context.data_pipeline.pipeline_status.add_step_result(
                            step_result
                        )

                        self._current_message_context.data_pipeline.save_to_persistent_storage(
                            self.application_context.configuration.app_storage_blob_url,
                            self.application_context.configuration.app_cps_processes,
                        )

                        pipeline_queue_helper.pass_data_pipeline_to_next_step(
                            self._current_message_context.data_pipeline,
                            self.application_context.configuration.app_storage_queue_url,
                            self.application_context.credential,
                        )

                        pipeline_queue_helper.delete_queue_message(
                            queue_message, self.queue_client
                        )

                        # Update Process Status to Cosmos DB
                        ContentProcess(
                            process_id=self._current_message_context.data_pipeline.pipeline_status.process_id,
                            processed_file_name=self._current_message_context.data_pipeline.files[
                                0
                            ].name,
                            processed_file_mime_type=self._current_message_context.data_pipeline.files[
                                0
                            ].mime_type,
                            status="Completed"
                            if self._current_message_context.data_pipeline.pipeline_status.completed
                            else step_name,
                            imported_time=datetime.datetime.strptime(
                                self._current_message_context.data_pipeline.pipeline_status.creation_time,
                                "%Y-%m-%dT%H:%M:%S.%fZ",
                            ),
                            last_modified_time=datetime.datetime.now(datetime.UTC),
                            last_modified_by=step_name,
                        ).update_process_status_to_cosmos(
                            connection_string=self.application_context.configuration.app_cosmos_connstr,
                            database_name=self.application_context.configuration.app_cosmos_database,
                            collection_name=self.application_context.configuration.app_cosmos_container_process,
                        )
                    else:
                        logging.error("Message is not a valid model.")
                        self._move_to_dead_letter_queue(queue_message)
                except Exception as e:
                    logging.error(f"Error Occurred: {e}")

                    def _get_artifact_type(step_name: str) -> ArtifactType:
                        if step_name == "extract":
                            return ArtifactType.ExtractedContent
                        elif step_name == "map":
                            return ArtifactType.SchemaMappedData
                        elif step_name == "evaluate":
                            return ArtifactType.ScoreMergedData
                        else:
                            return ArtifactType.Undefined

                    # Save the exception to the status object
                    if self._current_message_context is not None:
                        self._current_message_context.data_pipeline.pipeline_status.exception = e
                        exception_result = StepResult(
                            process_id=self._current_message_context.data_pipeline.pipeline_status.process_id,
                            step_name=self.handler_name,
                            result={
                                "result": "error",
                                "error": self._current_message_context.data_pipeline.pipeline_status.exception.model_dump_json(),
                            },
                        )

                        self._current_message_context.data_pipeline.pipeline_status.add_step_result(
                            exception_result
                        )

                        exception_result.save_to_persistent_storage(
                            account_url=self.application_context.configuration.app_storage_blob_url,
                            container_name=self.application_context.configuration.app_cps_processes,
                        )

                        self._current_message_context.data_pipeline.pipeline_status.save_to_persistent_storage(
                            account_url=self.application_context.configuration.app_storage_blob_url,
                            container_name=self.application_context.configuration.app_cps_processes,
                        )

                        # Only mark as terminal "Error" when retries are
                        # exhausted.  While retries remain, use "Retrying"
                        # so the workflow poller keeps waiting instead of
                        # treating the first transient failure as final.
                        has_retries_remaining = queue_message.dequeue_count <= 5

                        if has_retries_remaining:
                            # Lightweight status-only update — avoids
                            # overwriting the document with null result /
                            # scores that a previous successful step may
                            # have written.
                            ContentProcess(
                                process_id=self._current_message_context.data_pipeline.process_id,
                                processed_file_name=self._current_message_context.data_pipeline.files[
                                    0
                                ].name,
                                status="Retrying",
                                processed_file_mime_type=self._current_message_context.data_pipeline.files[
                                    0
                                ].mime_type,
                                last_modified_time=datetime.datetime.now(datetime.UTC),
                                last_modified_by=step_name,
                                imported_time=datetime.datetime.strptime(
                                    self._current_message_context.data_pipeline.pipeline_status.creation_time,
                                    "%Y-%m-%dT%H:%M:%S.%fZ",
                                ),
                            ).update_process_status_to_cosmos(
                                connection_string=self.application_context.configuration.app_cosmos_connstr,
                                database_name=self.application_context.configuration.app_cosmos_database,
                                collection_name=self.application_context.configuration.app_cosmos_container_process,
                            )
                        else:
                            ContentProcess(
                                process_id=self._current_message_context.data_pipeline.process_id,
                                processed_file_name=self._current_message_context.data_pipeline.files[
                                    0
                                ].name,
                                status="Error",
                                processed_file_mime_type=self._current_message_context.data_pipeline.files[
                                    0
                                ].mime_type,
                                last_modified_time=datetime.datetime.now(datetime.UTC),
                                last_modified_by=step_name,
                                imported_time=datetime.datetime.strptime(
                                    self._current_message_context.data_pipeline.pipeline_status.creation_time,
                                    "%Y-%m-%dT%H:%M:%S.%fZ",
                                ),
                                process_output=[
                                    Step_Outputs(
                                        step_name=self.handler_name,
                                        step_result=exception_result.result,
                                    )
                                ],
                            ).update_status_to_cosmos(
                                connection_string=self.application_context.configuration.app_cosmos_connstr,
                                database_name=self.application_context.configuration.app_cosmos_database,
                                collection_name=self.application_context.configuration.app_cosmos_container_process,
                            )

                        process_outputs: list[Step_Outputs] = []

                        if not has_retries_remaining:
                            logging.info(
                                "Message will be moved to the Dead Letter Queue."
                            )
                            dead_letter_result = StepResult(
                                process_id=self._current_message_context.data_pipeline.pipeline_status.process_id,
                                step_name=self.handler_name,
                                result={
                                    "result": "moved to Dead Letter Queue",
                                    "error": self._current_message_context.data_pipeline.pipeline_status.exception.model_dump_json(),
                                },
                            )

                            self._current_message_context.data_pipeline.pipeline_status.add_step_result(
                                exception_result
                            )

                            dead_letter_result.save_to_persistent_storage(
                                account_url=self.application_context.configuration.app_storage_blob_url,
                                container_name=self.application_context.configuration.app_cps_processes,
                            )

                            self._current_message_context.data_pipeline.pipeline_status.add_step_result(
                                dead_letter_result
                            )

                            self._current_message_context.data_pipeline.pipeline_status.save_to_persistent_storage(
                                account_url=self.application_context.configuration.app_storage_blob_url,
                                container_name=self.application_context.configuration.app_cps_processes,
                            )

                            pipeline_queue_helper.move_to_dead_letter_queue(
                                queue_message,
                                self.dead_letter_queue_client,
                                self.queue_client,
                            )

                            ContentProcess(
                                process_id=self._current_message_context.data_pipeline.process_id,
                                processed_file_name=self._current_message_context.data_pipeline.files[
                                    0
                                ].name,
                                processed_file_mime_type=self._current_message_context.data_pipeline.files[
                                    0
                                ].mime_type,
                                status="Error",
                                last_modified_time=datetime.datetime.now(datetime.UTC),
                                last_modified_by=step_name,
                                imported_time=datetime.datetime.strptime(
                                    self._current_message_context.data_pipeline.pipeline_status.creation_time,
                                    "%Y-%m-%dT%H:%M:%S.%fZ",
                                ),
                                process_output=[
                                    Step_Outputs(
                                        step_name=self.handler_name,
                                        step_result=dead_letter_result.result,
                                    )
                                ],
                            ).update_status_to_cosmos(
                                connection_string=self.application_context.configuration.app_cosmos_connstr,
                                database_name=self.application_context.configuration.app_cosmos_database,
                                collection_name=self.application_context.configuration.app_cosmos_container_process,
                            )

                            process_outputs.append(
                                Step_Outputs(
                                    step_name=self._current_message_context.data_pipeline.pipeline_status.active_step,
                                    processed_time="error",
                                    step_result=dead_letter_result,
                                )
                            )
                        else:
                            self.queue_client.update_message(
                                queue_message,
                                visibility_timeout=self.application_context.configuration.app_message_queue_visibility_timeout,
                            )

                            process_outputs.append(
                                Step_Outputs(
                                    step_name=self._current_message_context.data_pipeline.pipeline_status.active_step,
                                    processed_time="error",
                                    step_result=exception_result,
                                )
                            )

                        # Save step outputs to blob storage
                        processed_history = self._current_message_context.data_pipeline.add_file(
                            file_name="step_outputs.json",
                            artifact_type=_get_artifact_type(
                                self._current_message_context.data_pipeline.pipeline_status.active_step,
                            ),
                        )
                        processed_history.log_entries.append(
                            PipelineLogEntry(**{
                                "source": self.handler_name,
                                "message": "Process Output has been added. this file should be deserialized to Step_Outputs[]",
                            })
                        )

                        processed_history.upload_json_text(
                            account_url=self.application_context.configuration.app_storage_blob_url,
                            container_name=self.application_context.configuration.app_cps_processes,
                            text=json.dumps([
                                step.model_dump() for step in process_outputs
                            ]),
                        )

    def __initialize_handler(self, appContext: AppContext, step_name: str):
        """Set up queue clients and handler metadata for a pipeline step."""
        self.handler_name = step_name
        self.application_context = appContext

        self.queue_name = pipeline_queue_helper.create_queue_client_name(
            self.handler_name
        )

        self.dead_letter_queue_name = (
            pipeline_queue_helper.create_dead_letter_queue_client_name(
                self.handler_name
            )
        )

        self.queue_client = pipeline_queue_helper.create_or_get_queue_client(
            self.queue_name,
            self.application_context.configuration.app_storage_queue_url,
            self.application_context.credential,
        )
        self.dead_letter_queue_client = (
            pipeline_queue_helper.create_or_get_queue_client(
                self.dead_letter_queue_name,
                self.application_context.configuration.app_storage_queue_url,
                self.application_context.credential,
            )
        )
        self._show_queue_information()

    def _show_queue_information(self):
        """Log queue name, URL, and approximate message count."""
        queue_statue_message: str = """
        ************************************************************************************************
        * Queue Information - Initialized Successfully
        * Queue Name: {queue_name}
        * Queue URL: {queue_url}
        * Queue Message Count: {queue_message_count}
        ************************************************************************************************
        """
        queue_statue_message = queue_statue_message.format(
            queue_name=self.queue_name,
            queue_url=self.queue_client.url,
            queue_message_count=self.queue_client.get_queue_properties().approximate_message_count,
        )
        logging.info(queue_statue_message)
        print(queue_statue_message)

    @abstractmethod
    async def execute(self, context: MessageContext) -> StepResult:
        raise NotImplementedError("execute method is not implemented")

    def connect_queue(
        self,
        show_information: bool = True,
        app_context: AppContext = None,
        step_name: str = None,
    ):
        """
        Entry point for handlers to be hosted by process host and runs asynchronously.

        Args:
            show_information (bool, optional): If True, displays information about the connection process. Defaults to True.
            app_context (AppContext, optional): The application context to use for the connection. Defaults to None.
            step_name (str, optional): The name of the step in the pipeline. Defaults to None.
        """
        asyncio.run(
            self._connect_async(
                show_information=show_information,
                app_context=app_context,
                step_name=step_name,
            )
        )

    def download_output_file_to_json_string(
        self, processed_by: str, artifact_type: ArtifactType
    ):
        """
        Download the output file stream and convert it to a JSON string.

        Args:
            processed_by (str): The name of the step that processed the file.
            artifact_type (ArtifactType): The type of artifact.

        Returns:
            str: The output file as a JSON string.
        """
        output_files = [
            file
            for file in self._current_message_context.data_pipeline.files
            if file.processed_by == processed_by and file.artifact_type == artifact_type
        ]

        # Download the output file stream
        if output_files is None or len(output_files) == 0:
            output_file_stream = b""
        else:
            output_file_stream = output_files[0].download_stream(
                self.application_context.configuration.app_storage_blob_url,
                self.application_context.configuration.app_cps_processes,
            )

        # Convert the output file stream to a JSON string
        return output_file_stream.decode("utf-8")
