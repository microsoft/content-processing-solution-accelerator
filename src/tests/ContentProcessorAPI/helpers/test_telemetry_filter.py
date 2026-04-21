# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Unit tests for the OpenTelemetry span-noise filter."""

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "ContentProcessorAPI")))

from app.utils.telemetry_filter import install_noise_filter  # noqa: E402


@patch("app.utils.telemetry_filter.trace")
def test_install_noise_filter_no_active_processor(mock_trace):
    """Early return when the provider has no _active_span_processor."""
    mock_provider = MagicMock(spec=[])  # no attributes at all
    mock_trace.get_tracer_provider.return_value = mock_provider

    install_noise_filter(noisy_names=frozenset({"Foo"}))
    # Nothing to wrap, should return without error


@patch("app.utils.telemetry_filter.trace")
def test_install_noise_filter_wraps_inner_processors(mock_trace):
    """Wraps each processor in _span_processors tuple."""
    inner_proc_1 = MagicMock()
    inner_proc_2 = MagicMock()

    active_proc = MagicMock()
    active_proc._span_processors = (inner_proc_1, inner_proc_2)

    mock_provider = MagicMock()
    mock_provider._active_span_processor = active_proc
    mock_trace.get_tracer_provider.return_value = mock_provider

    install_noise_filter(
        noisy_names=frozenset({"NoisySpan"}),
        noisy_suffixes=(".noisy",),
    )

    # The tuple should have been replaced with wrapped processors
    assert len(active_proc._span_processors) == 2
    # Each element should be a _Filter wrapping the original
    for wrapped in active_proc._span_processors:
        assert hasattr(wrapped, "_inner")


@patch("app.utils.telemetry_filter.trace")
def test_install_noise_filter_wraps_direct_processor(mock_trace):
    """Wraps the processor directly when _span_processors is absent."""
    active_proc = MagicMock(spec=["on_start", "on_end", "shutdown", "force_flush"])
    # No _span_processors attribute

    mock_provider = MagicMock()
    mock_provider._active_span_processor = active_proc
    mock_trace.get_tracer_provider.return_value = mock_provider

    install_noise_filter(noisy_names=frozenset({"NoisySpan"}))

    # Provider should now have a wrapped processor
    new_proc = mock_provider._active_span_processor
    assert hasattr(new_proc, "_inner")
    assert new_proc._inner is active_proc


@patch("app.utils.telemetry_filter.trace")
def test_filter_on_start_delegates(mock_trace):
    """_Filter.on_start delegates to the inner processor."""
    inner_proc = MagicMock()
    active_proc = MagicMock()
    active_proc._span_processors = (inner_proc,)

    mock_provider = MagicMock()
    mock_provider._active_span_processor = active_proc
    mock_trace.get_tracer_provider.return_value = mock_provider

    install_noise_filter(noisy_names=frozenset({"NoisySpan"}))

    wrapped = active_proc._span_processors[0]
    mock_span = MagicMock()
    mock_context = MagicMock()
    wrapped.on_start(mock_span, mock_context)

    inner_proc.on_start.assert_called_once_with(mock_span, mock_context)


@patch("app.utils.telemetry_filter.trace")
def test_filter_on_end_drops_noisy_name(mock_trace):
    """_Filter.on_end drops spans whose name is in noisy_names."""
    inner_proc = MagicMock()
    active_proc = MagicMock()
    active_proc._span_processors = (inner_proc,)

    mock_provider = MagicMock()
    mock_provider._active_span_processor = active_proc
    mock_trace.get_tracer_provider.return_value = mock_provider

    install_noise_filter(noisy_names=frozenset({"MsiToken.Refresh"}))

    wrapped = active_proc._span_processors[0]
    mock_span = MagicMock()
    mock_span.name = "MsiToken.Refresh"
    wrapped.on_end(mock_span)

    inner_proc.on_end.assert_not_called()


@patch("app.utils.telemetry_filter.trace")
def test_filter_on_end_drops_noisy_suffix(mock_trace):
    """_Filter.on_end drops spans whose name ends with a noisy suffix."""
    inner_proc = MagicMock()
    active_proc = MagicMock()
    active_proc._span_processors = (inner_proc,)

    mock_provider = MagicMock()
    mock_provider._active_span_processor = active_proc
    mock_trace.get_tracer_provider.return_value = mock_provider

    install_noise_filter(noisy_suffixes=(" send", " receive"))

    wrapped = active_proc._span_processors[0]
    mock_span = MagicMock()
    mock_span.name = "ServiceBusReceiver receive"
    wrapped.on_end(mock_span)

    inner_proc.on_end.assert_not_called()


@patch("app.utils.telemetry_filter.trace")
def test_filter_on_end_passes_non_noisy(mock_trace):
    """_Filter.on_end passes through non-noisy spans."""
    inner_proc = MagicMock()
    active_proc = MagicMock()
    active_proc._span_processors = (inner_proc,)

    mock_provider = MagicMock()
    mock_provider._active_span_processor = active_proc
    mock_trace.get_tracer_provider.return_value = mock_provider

    install_noise_filter(
        noisy_names=frozenset({"NoisySpan"}),
        noisy_suffixes=(".noisy",),
    )

    wrapped = active_proc._span_processors[0]
    mock_span = MagicMock()
    mock_span.name = "ImportantOperation"
    wrapped.on_end(mock_span)

    inner_proc.on_end.assert_called_once_with(mock_span)


@patch("app.utils.telemetry_filter.trace")
def test_filter_shutdown_delegates(mock_trace):
    """_Filter.shutdown delegates to the inner processor."""
    inner_proc = MagicMock()
    active_proc = MagicMock()
    active_proc._span_processors = (inner_proc,)

    mock_provider = MagicMock()
    mock_provider._active_span_processor = active_proc
    mock_trace.get_tracer_provider.return_value = mock_provider

    install_noise_filter(noisy_names=frozenset())

    wrapped = active_proc._span_processors[0]
    wrapped.shutdown()

    inner_proc.shutdown.assert_called_once()


@patch("app.utils.telemetry_filter.trace")
def test_filter_force_flush_delegates(mock_trace):
    """_Filter.force_flush delegates to the inner processor."""
    inner_proc = MagicMock()
    active_proc = MagicMock()
    active_proc._span_processors = (inner_proc,)

    mock_provider = MagicMock()
    mock_provider._active_span_processor = active_proc
    mock_trace.get_tracer_provider.return_value = mock_provider

    install_noise_filter(noisy_names=frozenset())

    wrapped = active_proc._span_processors[0]
    wrapped.force_flush(timeout_millis=5000)

    inner_proc.force_flush.assert_called_once_with(5000)
