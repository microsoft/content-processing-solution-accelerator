# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs/agent_framework/agent_builder.py (fluent builder API)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from libs.agent_framework.agent_builder import AgentBuilder


def _fake_chat_client():
    """Return a minimal mock implementing ChatClientProtocol."""
    return MagicMock()


# ── Fluent builder ───────────────────────────────────────────────────────────


class TestFluentBuilder:
    def test_chaining_returns_self(self):
        client = _fake_chat_client()
        builder = AgentBuilder(client)
        result = (
            builder.with_name("Bot")
            .with_instructions("Be helpful.")
            .with_temperature(0.5)
            .with_max_tokens(100)
            .with_top_p(0.9)
        )
        assert result is builder

    def test_stores_all_attributes(self):
        client = _fake_chat_client()
        builder = (
            AgentBuilder(client)
            .with_name("Bot")
            .with_id("id-1")
            .with_description("desc")
            .with_instructions("instruct")
            .with_temperature(0.7)
            .with_max_tokens(500)
            .with_top_p(0.95)
            .with_frequency_penalty(0.1)
            .with_presence_penalty(0.2)
            .with_seed(42)
            .with_stop(["STOP"])
            .with_model_id("gpt-4")
            .with_user("user-1")
            .with_store(True)
            .with_conversation_id("conv-1")
        )
        assert builder._name == "Bot"
        assert builder._id == "id-1"
        assert builder._description == "desc"
        assert builder._instructions == "instruct"
        assert builder._temperature == 0.7
        assert builder._max_tokens == 500
        assert builder._top_p == 0.95
        assert builder._frequency_penalty == 0.1
        assert builder._presence_penalty == 0.2
        assert builder._seed == 42
        assert builder._stop == ["STOP"]
        assert builder._model_id == "gpt-4"
        assert builder._user == "user-1"
        assert builder._store is True
        assert builder._conversation_id == "conv-1"

    @patch("libs.agent_framework.agent_builder.ChatAgent")
    def test_build_delegates_to_chat_agent(self, mock_chat_agent):
        client = _fake_chat_client()
        mock_chat_agent.return_value = "agent_instance"

        agent = (
            AgentBuilder(client)
            .with_name("Bot")
            .with_instructions("Do stuff")
            .with_temperature(0.5)
            .build()
        )

        assert agent == "agent_instance"
        mock_chat_agent.assert_called_once()
        call_kwargs = mock_chat_agent.call_args
        assert call_kwargs.kwargs["name"] == "Bot"
        assert call_kwargs.kwargs["instructions"] == "Do stuff"
        assert call_kwargs.kwargs["temperature"] == 0.5


# ── Static factory ───────────────────────────────────────────────────────────


class TestStaticFactory:
    @patch("libs.agent_framework.agent_builder.ChatAgent")
    def test_create_agent_delegates_to_chat_agent(self, mock_chat_agent):
        client = _fake_chat_client()
        mock_chat_agent.return_value = "agent_instance"

        agent = AgentBuilder.create_agent(
            chat_client=client,
            name="Bot",
            instructions="instruct",
            temperature=0.3,
        )

        assert agent == "agent_instance"
        call_kwargs = mock_chat_agent.call_args
        assert call_kwargs.kwargs["name"] == "Bot"
        assert call_kwargs.kwargs["temperature"] == 0.3


# ── with_kwargs ──────────────────────────────────────────────────────────────


class TestWithKwargs:
    @patch("libs.agent_framework.agent_builder.ChatAgent")
    def test_extra_kwargs_forwarded(self, mock_chat_agent):
        client = _fake_chat_client()
        mock_chat_agent.return_value = "agent_instance"

        AgentBuilder(client).with_kwargs(custom_param="val").build()

        call_kwargs = mock_chat_agent.call_args
        assert call_kwargs.kwargs.get("custom_param") == "val"


# ── with_additional_chat_options ─────────────────────────────────────────────


class TestAdditionalChatOptions:
    def test_stores_options(self):
        client = _fake_chat_client()
        opts = {"reasoning": {"effort": "high"}}
        builder = AgentBuilder(client).with_additional_chat_options(opts)
        assert builder._additional_chat_options == opts


# ── with_response_format ─────────────────────────────────────────────────────


class TestResponseFormat:
    def test_stores_response_format(self):
        from pydantic import BaseModel

        class MyOutput(BaseModel):
            answer: str

        client = _fake_chat_client()
        builder = AgentBuilder(client).with_response_format(MyOutput)
        assert builder._response_format is MyOutput
