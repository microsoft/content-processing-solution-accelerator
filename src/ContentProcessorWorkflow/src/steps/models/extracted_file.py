# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Data model for a single document whose content has been extracted.

Used by the summarisation and gap-analysis executors to collect the
text (or structured JSON) that the content-processing API returned
for each file in the claim batch.
"""

from pydantic import BaseModel, Field


class ExtractedFile(BaseModel):
    """Intermediate representation of one extracted document.

    Attributes:
        file_name:         Original filename from the claim batch.
        mime_type:         Detected MIME type (defaults to
                           ``application/octet-stream``).
        extracted_content: Raw extracted text or JSON string returned
                           by the content-processing service.
    """

    file_name: str = Field(..., description="The name of the extracted file.")
    mime_type: str = Field(
        default="application/octet-stream",
        description="The MIME type of the extracted file.",
    )
    extracted_content: str = Field(
        ..., description="The content of the extracted file."
    )
