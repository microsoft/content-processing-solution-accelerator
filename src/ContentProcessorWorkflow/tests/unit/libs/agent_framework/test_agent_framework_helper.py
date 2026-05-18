# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs/agent_framework/agent_framework_helper.py."""

from __future__ import annotations

import pytest
from unittest.mock import patch

from libs.agent_framework.agent_framework_helper import (
    AgentFrameworkHelper,
    ClientType,
)


# ── ClientType enum ──────────────────────────────────────────────────────────


class TestClientType:
    def test_all_members_present(self):
        expected = {
            "OpenAIChatCompletion",
            "OpenAIAssistant",
            "OpenAIResponse",
            "AzureOpenAIChatCompletion",
            "AzureOpenAIChatCompletionWithRetry",
            "AzureOpenAIAssistant",
            "AzureOpenAIResponse",
            "AzureOpenAIResponseWithRetry",
            "AzureOpenAIAgent",
        }
        actual = {m.name for m in ClientType}
        assert actual == expected


# ── AgentFrameworkHelper ─────────────────────────────────────────────────────


class TestAgentFrameworkHelper:
    def test_init_creates_empty_registry(self):
        helper = AgentFrameworkHelper()
        assert helper.ai_clients == {}

    def test_initialize_raises_on_none_settings(self):
        helper = AgentFrameworkHelper()
        with pytest.raises(ValueError, match="AgentFrameworkSettings must be provided"):
            helper.initialize(None)

    def test_get_client_async_returns_none_for_unknown(self):
        import asyncio

        async def _run():
            helper = AgentFrameworkHelper()
            result = await helper.get_client_async("nonexistent")
            assert result is None

        asyncio.run(_run())

    def test_get_client_async_returns_cached(self):
        import asyncio

        async def _run():
            helper = AgentFrameworkHelper()
            helper.ai_clients["default"] = "mock_client"
            result = await helper.get_client_async("default")
            assert result == "mock_client"

        asyncio.run(_run())


# ── create_client ────────────────────────────────────────────────────────────


class TestCreateClient:
    def test_openai_chat_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            AgentFrameworkHelper.create_client(
                client_type=ClientType.OpenAIChatCompletion
            )

    def test_openai_assistant_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            AgentFrameworkHelper.create_client(client_type=ClientType.OpenAIAssistant)

    def test_openai_response_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            AgentFrameworkHelper.create_client(client_type=ClientType.OpenAIResponse)

    def test_unsupported_type_raises_value_error(self):
        with pytest.raises(ValueError, match="Unsupported agent type"):
            AgentFrameworkHelper.create_client(client_type="bogus_type")

    @patch("libs.agent_framework.agent_framework_helper.get_bearer_token_provider")
    def test_azure_chat_completion_creates_client(self, mock_token):
        mock_token.return_value = lambda: "token"

        with patch("agent_framework.azure.AzureOpenAIChatClient") as mock_cls:
            mock_cls.return_value = "chat_client"
            client = AgentFrameworkHelper.create_client(
                client_type=ClientType.AzureOpenAIChatCompletion,
                endpoint="https://example.openai.azure.com",
                deployment_name="gpt-4",
            )
            assert client == "chat_client"

    @patch("libs.agent_framework.agent_framework_helper.get_bearer_token_provider")
    def test_azure_response_creates_client(self, mock_token):
        mock_token.return_value = lambda: "token"

        with patch("agent_framework.azure.AzureOpenAIResponsesClient") as mock_cls:
            mock_cls.return_value = "response_client"
            client = AgentFrameworkHelper.create_client(
                client_type=ClientType.AzureOpenAIResponse,
                endpoint="https://example.openai.azure.com",
                deployment_name="gpt-4",
            )
            assert client == "response_client"
