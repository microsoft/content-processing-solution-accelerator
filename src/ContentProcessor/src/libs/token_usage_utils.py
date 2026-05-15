# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Token usage tracking for LLM calls in the content processing pipeline.

Extracts token counts from Azure OpenAI agent framework responses and emits
custom events to Application Insights for monitoring, cost estimation, and
performance optimization.
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def _track_event_if_configured(event_name: str, event_data: dict) -> None:
    """Track a custom event to Application Insights if configured.

    Args:
        event_name: Name of the custom event.
        event_data: Dictionary of event properties (all values must be strings).
    """
    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if connection_string:
        try:
            from azure.monitor.events.extension import track_event

            track_event(event_name, event_data)
        except Exception as exc:
            logger.warning("Failed to track event '%s': %s", event_name, exc)
    else:
        logger.debug(
            "Skipping track_event for %s: Application Insights is not configured",
            event_name,
        )


def extract_token_usage(response: Any) -> dict[str, int]:
    """Extract token usage from an agent framework ChatMessage response.

    Checks multiple attribute paths to handle different response shapes
    from the agent framework SDK.

    Args:
        response: The ChatMessage response object from agent.run().

    Returns:
        Dict with keys: input_tokens, output_tokens, total_tokens.
        All default to 0 if not found.
    """
    input_tokens = 0
    output_tokens = 0
    total_tokens = 0

    # Path 1: usage_details attribute (set by agent framework SDK)
    usage_details = getattr(response, "usage_details", None)
    if usage_details is not None:
        if isinstance(usage_details, dict):
            input_tokens = _to_int(
                usage_details.get("input_token_count")
                or usage_details.get("prompt_tokens")
                or usage_details.get("input_tokens")
            )
            output_tokens = _to_int(
                usage_details.get("output_token_count")
                or usage_details.get("completion_tokens")
                or usage_details.get("output_tokens")
            )
            total_tokens = _to_int(
                usage_details.get("total_token_count")
                or usage_details.get("total_tokens")
            ) or (input_tokens + output_tokens)
        else:
            # UsageDetails object with attributes
            input_tokens = _to_int(
                getattr(usage_details, "input_token_count", 0)
                or getattr(usage_details, "prompt_tokens", 0)
            )
            output_tokens = _to_int(
                getattr(usage_details, "output_token_count", 0)
                or getattr(usage_details, "completion_tokens", 0)
            )
            total_tokens = _to_int(
                getattr(usage_details, "total_token_count", 0)
            ) or (input_tokens + output_tokens)

    # Path 2: raw_representation.usage (raw Azure OpenAI response)
    if total_tokens == 0:
        raw = getattr(response, "raw_representation", None)
        if raw is not None:
            usage_obj = getattr(raw, "usage", None)
            if usage_obj is not None:
                if isinstance(usage_obj, dict):
                    input_tokens = _to_int(
                        usage_obj.get("prompt_tokens")
                        or usage_obj.get("input_tokens")
                    )
                    output_tokens = _to_int(
                        usage_obj.get("completion_tokens")
                        or usage_obj.get("output_tokens")
                    )
                    total_tokens = _to_int(
                        usage_obj.get("total_tokens")
                    ) or (input_tokens + output_tokens)
                else:
                    input_tokens = _to_int(
                        getattr(usage_obj, "prompt_tokens", 0)
                        or getattr(usage_obj, "input_tokens", 0)
                    )
                    output_tokens = _to_int(
                        getattr(usage_obj, "completion_tokens", 0)
                        or getattr(usage_obj, "output_tokens", 0)
                    )
                    total_tokens = _to_int(
                        getattr(usage_obj, "total_tokens", 0)
                    ) or (input_tokens + output_tokens)

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }


def emit_agent_token_event(
    agent_name: str,
    model_deployment_name: str,
    usage: dict[str, int],
    process_id: str = "",
) -> None:
    """Emit a per-agent token usage event to Application Insights.

    Args:
        agent_name: Name of the pipeline step/agent (e.g. 'MapHandler', 'RAI').
        model_deployment_name: Azure OpenAI model deployment name.
        usage: Dict with input_tokens, output_tokens, total_tokens.
        process_id: Document processing ID for correlation.
    """
    _track_event_if_configured("LLM_Agent_Token_Usage", {
        "agent_name": agent_name,
        "input_tokens": str(usage.get("input_tokens", 0)),
        "output_tokens": str(usage.get("output_tokens", 0)),
        "total_tokens": str(usage.get("total_tokens", 0)),
        "model_deployment_name": model_deployment_name,
        "process_id": process_id,
    })
    logger.info(
        "[TOKEN USAGE] agent=%s model=%s input=%d output=%d total=%d process=%s",
        agent_name,
        model_deployment_name,
        usage.get("input_tokens", 0),
        usage.get("output_tokens", 0),
        usage.get("total_tokens", 0),
        process_id,
    )


def emit_model_token_event(
    model_deployment_name: str,
    usage: dict[str, int],
    process_id: str = "",
) -> None:
    """Emit a per-model token usage event to Application Insights.

    Args:
        model_deployment_name: Azure OpenAI model deployment name.
        usage: Dict with input_tokens, output_tokens, total_tokens.
        process_id: Document processing ID for correlation.
    """
    _track_event_if_configured("LLM_Model_Token_Usage", {
        "model_deployment_name": model_deployment_name,
        "input_tokens": str(usage.get("input_tokens", 0)),
        "output_tokens": str(usage.get("output_tokens", 0)),
        "total_tokens": str(usage.get("total_tokens", 0)),
        "process_id": process_id,
    })


def emit_summary_token_event(
    total_input_tokens: int,
    total_output_tokens: int,
    total_tokens: int,
    process_id: str = "",
    file_name: str = "",
    file_mime_type: str = "",
    agent_count: int = 0,
    model_count: int = 0,
) -> None:
    """Emit a summary token usage event for a complete document processing run.

    Args:
        total_input_tokens: Sum of all input tokens across all steps.
        total_output_tokens: Sum of all output tokens across all steps.
        total_tokens: Sum of all tokens across all steps.
        process_id: Document processing ID.
        file_name: Name of the processed file.
        file_mime_type: MIME type of the processed file.
        agent_count: Number of agents/steps that used tokens.
        model_count: Number of distinct models used.
    """
    _track_event_if_configured("LLM_Token_Usage_Summary", {
        "total_input_tokens": str(total_input_tokens),
        "total_output_tokens": str(total_output_tokens),
        "total_tokens": str(total_tokens),
        "process_id": process_id,
        "file_name": file_name,
        "file_mime_type": file_mime_type,
        "agent_count": str(agent_count),
        "model_count": str(model_count),
    })
    logger.info(
        "[TOKEN SUMMARY] process=%s file=%s input=%d output=%d total=%d agents=%d models=%d",
        process_id,
        file_name,
        total_input_tokens,
        total_output_tokens,
        total_tokens,
        agent_count,
        model_count,
    )


def _to_int(val: object, default: int = 0) -> int:
    """Safely convert a value to int.

    Args:
        val: Value to convert.
        default: Default if conversion fails.

    Returns:
        Integer value or default.
    """
    if val is None or isinstance(val, bool):
        return default
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val)
    if isinstance(val, str):
        s = val.strip()
        if s.isdigit():
            return int(s)
    return default
