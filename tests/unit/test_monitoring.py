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
