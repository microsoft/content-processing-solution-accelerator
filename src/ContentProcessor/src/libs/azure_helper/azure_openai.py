# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import logging
from urllib.parse import urlparse

from helpers.azure_credential_utils import get_azure_credential
from azure.ai.inference import ChatCompletionsClient

logger = logging.getLogger(__name__)


def get_foundry_client(ai_services_endpoint: str) -> ChatCompletionsClient:
    """
    Return an Azure AI Inference ChatCompletionsClient using the
    Azure AI Foundry / AI Services endpoint (project / hub endpoint).
    Matches implementation from Conversation-Knowledge-Mining-Solution-Accelerator PR #632.
    """
    # Extract hostname and construct /models endpoint
    # ai_services_endpoint format: "https://<your-hub>.services.ai.azure.com/api/projects/<project-name>"
    parsed = urlparse(ai_services_endpoint)
    inference_endpoint = f"https://{parsed.netloc}/models"
    
    credential = get_azure_credential()
    
    # Create client without api_version parameter (as per KM PR #632)
    # The /models endpoint handles API versioning automatically
    return ChatCompletionsClient(
        endpoint=inference_endpoint,
        credential=credential,
        credential_scopes=["https://ai.azure.com/.default"],
    )
