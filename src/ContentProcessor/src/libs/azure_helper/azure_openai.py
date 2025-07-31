# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from azure.identity import get_bearer_token_provider
from helpers.azure_credential_utils import get_azure_credential
from openai import AzureOpenAI


def get_openai_client(azure_openai_endpoint: str) -> AzureOpenAI:
    credential = get_azure_credential()
    token_provider = get_bearer_token_provider(
        credential, "https://cognitiveservices.azure.com/.default"
    )
    return AzureOpenAI(
        azure_endpoint=azure_openai_endpoint,
        azure_ad_token_provider=token_provider,
        api_version="2024-10-01-preview",
    )
