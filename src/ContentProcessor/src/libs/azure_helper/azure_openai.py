# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from urllib.parse import urlparse
from helpers.azure_credential_utils import get_azure_credential
from azure.ai.inference import ChatCompletionsClient


def get_foundry_client(ai_services_endpoint: str) -> ChatCompletionsClient:
    parsed = urlparse(ai_services_endpoint)
    inference_endpoint = f"https://{parsed.netloc}/models"

    credential = get_azure_credential()

    return ChatCompletionsClient(
        endpoint=inference_endpoint,
        credential=credential,
        credential_scopes=["https://ai.azure.com/.default"],
    )
