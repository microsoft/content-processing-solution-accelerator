# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
from __future__ import annotations

"""Unit tests for AgentInfo model."""

from libs.agent_framework.agent_info import AgentInfo


def test_update_prompt_renders_jinja_template() -> None:
    rendered = AgentInfo.update_prompt("Hello {{ name }}!", name="Ada")
    assert rendered == "Hello Ada!"


def test_render_updates_system_prompt_and_instruction_templates() -> None:
    agent = AgentInfo(
        agent_name="TestAgent",
        agent_system_prompt="System: {{ system_value }}",
        agent_instruction="Do {{ action }}",
    )

    agent.render(system_value="S1", action="work")

    assert agent.agent_system_prompt == "System: S1"
    assert agent.agent_instruction == "Do work"


def test_render_leaves_plain_strings_unchanged() -> None:
    agent = AgentInfo(
        agent_name="TestAgent",
        agent_system_prompt="No templates here",
        agent_instruction="Also plain",
    )

    agent.render(anything="ignored")

    assert agent.agent_system_prompt == "No templates here"
    assert agent.agent_instruction == "Also plain"
