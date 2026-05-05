# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Utility for tracking custom events to Application Insights."""

import logging
import os

from azure.monitor.events.extension import track_event

logger = logging.getLogger(__name__)


def track_event_if_configured(event_name: str, event_data: dict):
    """Track custom event to Application Insights if configured.

    Args:
        event_name: Name of the event to track.
        event_data: Dictionary of event properties.
    """
    instrumentation_key = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if instrumentation_key:
        track_event(event_name, event_data)
    else:
        logger.warning(
            "Skipping track_event for %s: Application Insights is not configured",
            event_name,
        )
