# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import datetime
from enum import Enum
from typing import Optional

from pydantic import Field

from libs.azure_helper.storage_blob import StorageBlobHelper
from libs.base.application_models import AppModelBase


class ArtifactType(str, Enum):
    Undefined = "undefined"
    ConvertedContent = "converted_content"
    ExtractedContent = "extracted_content"
    SchemaMappedData = "schema_mapped_data"
    ScoreMergedData = "score_merged_data"
    SourceContent = "source_content"
    SavedContent = "saved_content"


class PipelineLogEntry(AppModelBase):
    """
    This is Pipeline Log Entry Model.
    This object will be used to store the log entries of the pipeline.
    """

    datetime_offset: str = datetime.datetime.now(datetime.UTC).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    source: str
    message: str


class FileDetailBase(AppModelBase):
    """
    Represents the base details of a file in the pipeline.
    Attributes:
        id (Optional[str]): The unique identifier of the file.
        process_id (str): The identifier of the process associated with the file.
        name (Optional[str]): The name of the file.
        size (Optional[int]): The size of the file in bytes.
        mime_type (Optional[str]): The MIME type of the file.
        artifact_type (Optional[ArtifactType]): The type of artifact the file represents.
        processed_by (Optional[str]): The step name of the entity that processed the file.
        log_entries (list[PipelineLogEntry]): A list of log entries associated with the file.
    Methods:
        add_log_entry(log_entry: PipelineLogEntry):
            Adds a log entry to the file's log entries.
    """

    id: Optional[str] = None
    process_id: str
    name: Optional[str] = None
    size: Optional[int] = None
    mime_type: Optional[str] = None
    artifact_type: Optional[ArtifactType] = None
    processed_by: Optional[str] = None
    log_entries: list[PipelineLogEntry] = Field(default_factory=list)

    def add_log_entry(self, source: str, message: str):
        self.log_entries.append(PipelineLogEntry(source=source, message=message))
        return self


class FileDetails(FileDetailBase):
    def download_stream(self, account_url: str, container_name: str) -> bytes:
        """
        Download the file locally
        """
        return StorageBlobHelper(
            account_url=account_url, container_name=container_name
        ).download_stream(container_name=self.process_id, blob_name=self.name)

    def download_file(self, account_url: str, container_name: str, file_path: str):
        """
        Download the file locally
        """
        StorageBlobHelper(
            account_url=account_url, container_name=container_name
        ).download_file(
            container_name=self.process_id, blob_name=self.name, download_path=file_path
        )

    def upload_stream(self, account_url: str, container_name: str, stream: bytes):
        """
        Upload the stream to the blob
        """
        StorageBlobHelper(
            account_url=account_url, container_name=container_name
        ).upload_stream(
            container_name=self.process_id, blob_name=self.name, stream=stream
        )
        self.size = len(stream)

    def upload_json_text(self, account_url: str, container_name: str, text: str):
        """
        Upload the json text to the blob
        """
        StorageBlobHelper(
            account_url=account_url, container_name=container_name
        ).upload_text(container_name=self.process_id, blob_name=self.name, text=text)
        self.size = len(text)
        self.mime_type = "application/json"
