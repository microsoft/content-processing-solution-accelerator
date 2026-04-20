# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
from __future__ import annotations

"""Unit tests for GroupChatOrchestrator termination logic."""

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime

from libs.agent_framework.groupchat_orchestrator import GroupChatOrchestrator


@dataclass
class _Msg:
    source: str
    content: str


def _make_orchestrator() -> GroupChatOrchestrator:
    return GroupChatOrchestrator(
        name="t",
        process_id="p1",
        participants={"Coordinator": object()},
        memory_client=None,  # not used by _complete_agent_response
        coordinator_name="Coordinator",
        result_output_format=None,
    )


def test_coordinator_complete_terminates_when_selected_participant_none_even_without_finish_true():
    async def _run():
        orch = _make_orchestrator()

        # Everyone who participated signed off PASS.
        orch._conversation = [
            _Msg(source="AKS Expert", content="SIGN-OFF: PASS"),
            _Msg(source="Chief Architect", content="SIGN-OFF: PASS"),
        ]

        orch._current_agent_start_time = datetime.now()
        orch._current_agent_response = [
            json.dumps({
                "selected_participant": None,
                "instruction": "complete",
                "finish": False,
                "final_message": "done",
            })
        ]

        await orch._complete_agent_response("Coordinator", callback=None)

        assert orch._termination_requested is True
        assert orch._termination_instruction == "complete"
        assert orch._termination_final_message == "done"

    asyncio.run(_run())


def test_coordinator_complete_rejected_when_signoffs_missing():
    async def _run():
        orch = _make_orchestrator()

        # Agent participated but never produced a SIGN-OFF.
        orch._conversation = [
            _Msg(source="AKS Expert", content="Reviewed; looks good."),
        ]

        orch._current_agent_start_time = datetime.now()
        orch._current_agent_response = [
            json.dumps({
                "selected_participant": None,
                "instruction": "complete",
                "finish": False,
                "final_message": "done",
            })
        ]

        await orch._complete_agent_response("Coordinator", callback=None)

        assert orch._termination_requested is False

    asyncio.run(_run())


def test_loop_detection_resets_when_other_agent_makes_progress_between_repeated_selections():
    async def _run():
        orch = _make_orchestrator()
        orch._conversation = []

        def _coordinator_select(participant: str, instruction: str = "do"):
            orch._current_agent_start_time = datetime.now()
            orch._current_agent_response = [
                json.dumps({
                    "selected_participant": participant,
                    "instruction": instruction,
                    "finish": False,
                    "final_message": "",
                })
            ]

        def _agent_reply(text: str = "ok"):
            orch._current_agent_start_time = datetime.now()
            orch._current_agent_response = [text]

        # 1) Coordinator selects the same participant.
        _coordinator_select("Chief Architect")
        await orch._complete_agent_response("Coordinator", callback=None)

        # 2) The participant responds (progress).
        _agent_reply("progress")
        await orch._complete_agent_response("Chief Architect", callback=None)

        # 3) Coordinator repeats the same selection twice.
        _coordinator_select("Chief Architect")
        await orch._complete_agent_response("Coordinator", callback=None)
        _coordinator_select("Chief Architect")
        await orch._complete_agent_response("Coordinator", callback=None)

        # With the progress-reset behavior, this should NOT have tripped the 3x loop breaker.
        assert orch._forced_termination_requested is False

    asyncio.run(_run())
