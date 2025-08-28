"""Metrics - A1 Agentic System

Prometheus metrics exports and simple helper functions used across the
project.  The existing :class:`~monitoring.metrics_collector.MetricsCollector`
is still re-exported for backwards compatibility, but this module now exposes
runtime gauges and counters that can be scraped by Prometheus.

The following metrics are provided:

``heartbeat``
    Timestamp of the last heartbeat emitted by the orchestrator.
``queue_depth``
    Number of tasks currently waiting for execution.
``error_rate``
    Rate of tool execution errors per second.
``errors_total``
    Counter of total tool execution errors.

The ``start_metrics_server`` function should be called once on start-up to
expose the ``/metrics`` HTTP endpoint (default port ``8000``).
"""

from __future__ import annotations

import time
from typing import Optional

from prometheus_client import Counter, Gauge, start_http_server

from .metrics_collector import MetricsCollector, MetricPoint

_start_time = time.time()
_error_count = 0

heartbeat_gauge = Gauge("a1_heartbeat", "Last recorded heartbeat timestamp")
queue_depth_gauge = Gauge("a1_queue_depth", "Current depth of the task queue")
error_counter = Counter("a1_errors_total", "Total number of tool errors")
error_rate_gauge = Gauge("a1_error_rate", "Tool error rate per second")


def start_metrics_server(port: int = 8000) -> None:
    """Start the Prometheus metrics HTTP server on the given ``port``."""

    start_http_server(port)


def record_heartbeat(timestamp: Optional[float] = None) -> None:
    """Update the heartbeat metric with ``timestamp`` or the current time."""

    heartbeat_gauge.set(timestamp or time.time())


def set_queue_depth(depth: int) -> None:
    """Set the current task queue ``depth`` metric."""

    queue_depth_gauge.set(depth)


def record_error() -> None:
    """Increment error counters and update the error rate gauge."""

    global _error_count
    _error_count += 1
    error_counter.inc()
    elapsed = time.time() - _start_time
    if elapsed > 0:
        error_rate_gauge.set(_error_count / elapsed)


__all__ = [
    "MetricsCollector",
    "MetricPoint",
    "start_metrics_server",
    "record_heartbeat",
    "set_queue_depth",
    "record_error",
]

