# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from azure.ai.projects import AIProjectClient
from helpers.azure_credential_utils import get_azure_credential


def get_foundry_client(ai_project_endpoint: str):
    """
    Create an OpenAI-compatible client via Azure AI Foundry (Projects SDK).

    This function uses the Azure AI Foundry approach:
    1. Create an AIProjectClient with the AI project endpoint
    2. Call .get_openai_client() to get an OpenAI-compatible client

    Args:
        ai_project_endpoint: The AI Foundry project endpoint URL (e.g., https://aif-xyz.services.ai.azure.com)

    Returns:
        An OpenAI-compatible client from the AI Foundry project
    """
    credential = get_azure_credential()
    
    # Create the AI Foundry Project client
    project_client = AIProjectClient(
        endpoint=ai_project_endpoint,
        credential=credential
    )
    
    # Get the OpenAI-compatible client from the project
    # This client supports .beta.chat.completions.parse() and other OpenAI methods
    return project_client.get_openai_client()
