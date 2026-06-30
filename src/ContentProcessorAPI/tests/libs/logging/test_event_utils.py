# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Unit tests for event_utils module."""

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from app.libs.logging.event_utils import track_event_if_configured  # noqa: E402


@patch("app.libs.logging.event_utils.track_event")
@patch.dict(os.environ, {"APPLICATIONINSIGHTS_CONNECTION_STRING": "InstrumentationKey=test-key"})
def test_track_event_when_configured(mock_track_event):
    """Track event should be called when APPLICATIONINSIGHTS_CONNECTION_STRING is set."""
    event_data = {"process_id": "123", "file_name": "test.pdf"}
    track_event_if_configured("FileSubmitted", event_data)

    mock_track_event.assert_called_once_with("FileSubmitted", event_data)


@patch("app.libs.logging.event_utils.track_event")
@patch.dict(os.environ, {}, clear=True)
def test_skip_track_event_when_not_configured(mock_track_event):
    """Track event should not be called when APPLICATIONINSIGHTS_CONNECTION_STRING is not set."""
    # Ensure the env var is not present
    os.environ.pop("APPLICATIONINSIGHTS_CONNECTION_STRING", None)

    event_data = {"process_id": "456"}
    track_event_if_configured("ProcessStatusQueried", event_data)

    mock_track_event.assert_not_called()


@patch("app.libs.logging.event_utils.track_event")
@patch.dict(os.environ, {"APPLICATIONINSIGHTS_CONNECTION_STRING": ""})
def test_skip_track_event_when_empty_string(mock_track_event):
    """Track event should not be called when APPLICATIONINSIGHTS_CONNECTION_STRING is empty."""
    track_event_if_configured("SomeEvent", {"key": "val"})

    mock_track_event.assert_not_called()


@patch("app.libs.logging.event_utils.track_event")
@patch.dict(os.environ, {"APPLICATIONINSIGHTS_CONNECTION_STRING": "InstrumentationKey=abc"})
def test_track_event_passes_correct_data(mock_track_event):
    """Verify event name and data are passed correctly to track_event."""
    event_data = {"claim_id": "c-789", "error": "timeout"}
    track_event_if_configured("ClaimProcessError", event_data)

    mock_track_event.assert_called_once_with("ClaimProcessError", event_data)
