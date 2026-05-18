# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""AI Foundry / Azure OpenAI inference client factory.

Constructs a ``ChatCompletionsClient`` authenticated via the shared
Azure credential for use by pipeline handlers and the agent framework.
"""

from urllib.parse import urlparse

from azure.ai.inference import ChatCompletionsClient

from libs.utils.azure_credential_utils import get_azure_credential


def get_foundry_client(ai_services_endpoint: str) -> ChatCompletionsClient:
    """Create a ChatCompletionsClient for the given AI Services endpoint.

    Args:
        ai_services_endpoint: Full URL of the AI Services resource.

    Returns:
        An authenticated ChatCompletionsClient targeting the ``/models`` path.
    """
    parsed = urlparse(ai_services_endpoint)
    inference_endpoint = f"https://{parsed.netloc}/models"

    credential = get_azure_credential()

    return ChatCompletionsClient(
        endpoint=inference_endpoint,
        credential=credential,
        credential_scopes=["https://ai.azure.com/.default"],
    )
