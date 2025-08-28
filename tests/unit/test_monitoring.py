"""Unit tests for monitoring utilities."""

import time
import queue

from monitoring.metrics_collector import MetricsCollector
from monitoring.watchdog import WorkerWatchdog


def test_heartbeat_and_queue_depth():
    metrics = MetricsCollector({"ENABLE_METRICS": True})
    metrics.start_heartbeat("unit", interval=0.05)
    time.sleep(0.12)
    assert metrics.get_last_heartbeat("unit") > 0

    q = queue.Queue()
    q.put(1)
    q.put(2)
    metrics.record_queue_depth("jobs", q.qsize())
    assert metrics.gauges["queue_jobs_depth"] == 2


def test_watchdog_restarts_and_alerts():
    metrics = MetricsCollector({"ENABLE_METRICS": True})

    def flaky_worker():
        metrics.record_heartbeat("worker")
        # simulate immediate exit / stall
        return

    watchdog = WorkerWatchdog(
        worker_fn=flaky_worker,
        metrics=metrics,
        heartbeat_name="worker",
        check_interval=0.05,
        stall_threshold=0.04,
        max_restarts=1,
    )
    watchdog.start()
    time.sleep(0.2)

    assert metrics.counters["watchdog_restarts"] >= 1
    assert metrics.counters["watchdog_alerts"] >= 1


def test_watchdog_resets_heartbeat_on_restart():
    metrics = MetricsCollector({"ENABLE_METRICS": True})
    # Seed an old heartbeat value
    metrics.record_heartbeat("worker")
    old = metrics.get_last_heartbeat("worker")
    time.sleep(0.01)

    watchdog = WorkerWatchdog(
        worker_fn=lambda: None,
        metrics=metrics,
        heartbeat_name="worker",
    )

    # Starting the worker should reset the heartbeat timestamp
    watchdog._start_worker()
    new = metrics.get_last_heartbeat("worker")

    assert new > old
