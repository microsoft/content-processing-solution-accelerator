# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Reusable OpenTelemetry span-noise filter.

Installs a thin wrapper around the active span processors that silently
drops ``on_end`` for span names matching caller-supplied patterns.  This
keeps low-value, high-frequency spans (MSI token refreshes, HTTP
send/receive, queue polling, etc.) out of Application Insights without
affecting useful telemetry.
"""

import logging

from opentelemetry import trace
from opentelemetry.sdk.trace import SpanProcessor

logger = logging.getLogger(__name__)


def install_noise_filter(
    *,
    noisy_names: frozenset[str] = frozenset(),
    noisy_suffixes: tuple[str, ...] = (),
) -> None:
    """Wrap every active span processor with a drop filter.

    Parameters
    ----------
    noisy_names:
        Exact span names to suppress (checked via ``in``).
    noisy_suffixes:
        Span-name suffixes to suppress (checked via ``str.endswith``).
    """

    class _Filter(SpanProcessor):
        """Delegates to *inner* but silently drops noisy spans on end."""

        def __init__(self, inner: SpanProcessor):
            self._inner = inner

        def on_start(self, span, parent_context=None):
            self._inner.on_start(span, parent_context)

        def on_end(self, span):
            name = span.name
            if name in noisy_names or (noisy_suffixes and name.endswith(noisy_suffixes)):
                return
            self._inner.on_end(span)

        def shutdown(self):
            self._inner.shutdown()

        def force_flush(self, timeout_millis=30000):
            return self._inner.force_flush(timeout_millis)

    provider = trace.get_tracer_provider()
    proc = getattr(provider, "_active_span_processor", None)
    if proc is None:
        return

    # Mutate the inner tuple so existing tracers (which cache a reference
    # to this SynchronousMultiSpanProcessor) pick up the filter.
    inner = getattr(proc, "_span_processors", None)
    if inner is not None:
        proc._span_processors = tuple(_Filter(p) for p in inner)  # noqa: SLF001
    else:
        provider._active_span_processor = _Filter(proc)  # noqa: SLF001

    logger.info("Telemetry noise filter installed (dropping %d name patterns)", len(noisy_names) + len(noisy_suffixes))
