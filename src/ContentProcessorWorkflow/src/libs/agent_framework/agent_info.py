# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Agent metadata container with Jinja2 template rendering.

This module defines ``AgentInfo``, a Pydantic model that bundles the configuration
needed to instantiate a ``ChatAgent`` via ``AgentBuilder.create_agent_by_agentinfo``:

- **Identity** — agent name, description, and ``ClientType`` selector.
- **Prompts** — a system prompt *or* an instruction string, either of which may
  contain Jinja2 ``{{ }}`` / ``{% %}`` syntax that is resolved at render time.
- **Tools** — optional tool protocols, callables, or MCP tool sequences.
- **Helper reference** — an ``AgentFrameworkHelper`` that provides the client
  factory and settings needed to build the underlying chat client.

Typical lifecycle:
    1. Create an ``AgentInfo`` with static prompt templates.
    2. Call ``agent_info.render(**runtime_vars)`` to resolve Jinja2 placeholders.
    3. Pass the rendered ``AgentInfo`` to ``AgentBuilder.create_agent_by_agentinfo``.
"""

from typing import Any, Callable, MutableMapping, Sequence

from agent_framework import ToolProtocol
from jinja2 import Template
from openai import BaseModel
from pydantic import Field

from .agent_framework_helper import AgentFrameworkHelper, ClientType


class AgentInfo(BaseModel):
    """Immutable metadata bundle for a single ChatAgent.

    Fields
    ------
    agent_name : str
        Display name used as the agent's identity in GroupChat conversations.
    agent_type : ClientType
        Which Azure OpenAI client variant to construct (Response, Chat, Assistant, …).
    agent_system_prompt : str | None
        Legacy system-level prompt. Supports Jinja2 templates.
    agent_description : str | None
        Short human-readable description (shown in orchestrator logs).
    agent_instruction : str | None
        Preferred instruction string (takes precedence over ``agent_system_prompt``
        when both are set). Supports Jinja2 templates.
    agent_framework_helper : AgentFrameworkHelper | None
        Reference to the shared helper that owns client settings and cached clients.
    tools : ToolProtocol | Callable | Sequence | None
        Tools to bind to the agent (MCP tools, plain callables, or tool dicts).
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
    def update_prompt(template: str, **kwargs) -> str:
        """Render a Jinja2 prompt template with the given variables.

        This is a convenience wrapper around ``jinja2.Template.render`` for
        one-off prompt rendering when you do not need to mutate an ``AgentInfo``
        instance.

        Args:
            template: A Jinja2 template string (e.g. ``"Summarize {{ document }}"``).
            **kwargs: Variable bindings passed to the Jinja2 renderer.

        Returns:
            The fully rendered prompt string.
        """
        return Template(template).render(**kwargs)

    def render(self, **kwargs) -> "AgentInfo":
        """Resolve Jinja2 placeholders in prompt fields and return self.

        Scans ``agent_system_prompt`` and ``agent_instruction`` for Jinja2
        delimiters (``{{ }}`` or ``{% %}``) and renders them in-place using
        the provided keyword arguments.

        Processing steps:
            1. If ``agent_system_prompt`` contains Jinja2 syntax, render it.
            2. If ``agent_instruction`` contains Jinja2 syntax, render it.
            3. Return ``self`` to allow method chaining.

        Args:
            **kwargs: Variable bindings forwarded to ``jinja2.Template.render``.

        Returns:
            The same ``AgentInfo`` instance with prompt fields resolved.

        Note:
            This mutates the instance. Call on a copy if the original template
            needs to be preserved for later re-renders with different variables.
        """
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
