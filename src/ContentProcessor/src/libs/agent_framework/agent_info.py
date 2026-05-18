# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Declarative agent metadata with Jinja2 template rendering.

Used to define agent configuration (name, prompts, tools, type) that
can be rendered with runtime context before constructing a ChatAgent.
"""

from typing import Any, Callable, MutableMapping, Sequence

from agent_framework import ToolProtocol
from jinja2 import Template
from openai import BaseModel
from pydantic import Field

from .agent_framework_helper import AgentFrameworkHelper, ClientType


class AgentInfo(BaseModel):
    """Declarative metadata for an agent, supporting Jinja2 template rendering.

    Attributes:
        agent_name: Display name of the agent.
        agent_type: Client type to use (default: AzureOpenAIResponse).
        agent_system_prompt: Optional system prompt (supports Jinja2 templates).
        agent_instruction: Optional instruction text (supports Jinja2 templates).
        agent_framework_helper: Helper instance for client creation.
        tools: Optional tools to attach to the agent.
    """

    agent_name: str
    agent_type: ClientType = Field(default=ClientType.AzureOpenAIResponse)
    agent_system_prompt: str | None = Field(default=None)
    agent_description: str | None = Field(default=None)
    agent_instruction: str | None = Field(default=None)
    agent_framework_helper: AgentFrameworkHelper | None = Field(default=None)
    tools: (
        ToolProtocol
        | Callable[..., Any]
        | MutableMapping[str, Any]
        | Sequence[ToolProtocol | Callable[..., Any] | MutableMapping[str, Any]]
        | None
    ) = Field(default=None)

    model_config = {
        "arbitrary_types_allowed": True,
    }

    @staticmethod
    def update_prompt(template: str, **kwargs):
        return Template(template).render(**kwargs)

    def render(self, **kwargs) -> "AgentInfo":
        """Simple template rendering method"""
        # Render agent_system_prompt if it contains Jinja templates
        if self.agent_system_prompt and (
            "{{" in self.agent_system_prompt or "{%" in self.agent_system_prompt
        ):
            self.agent_system_prompt = Template(self.agent_system_prompt).render(
                **kwargs
            )
        # Render agent_instruction if it exists and contains templates
        if self.agent_instruction and (
            "{{" in self.agent_instruction or "{%" in self.agent_instruction
        ):
            self.agent_instruction = Template(self.agent_instruction).render(**kwargs)
        return self
