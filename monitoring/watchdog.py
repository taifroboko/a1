"""Worker watchdog for monitoring and restarting stalled workers."""

from __future__ import annotations

import time
import threading
import logging
from typing import Callable, Optional

from .metrics_collector import MetricsCollector

logger = logging.getLogger(__name__)


class WorkerWatchdog:
    """Monitor a worker function and restart it if it stalls.

    Parameters
    ----------
    worker_fn:
        Callable that starts the worker when invoked. It should update a
        heartbeat in the provided :class:`MetricsCollector`.
    metrics:
        Metrics collector instance used for heartbeats and restart counters.
    heartbeat_name:
        Name of the heartbeat gauge to monitor.
    check_interval:
        How often to check for stalled workers (seconds).
    stall_threshold:
        If no heartbeat is recorded for this many seconds the worker is
        considered stalled and will be restarted.
    max_restarts:
        Number of automatic restarts before an alert is emitted.
    """

    def __init__(
        self,
        worker_fn: Callable[[], None],
        metrics: MetricsCollector,
        heartbeat_name: str = "worker",
        check_interval: float = 10.0,
        stall_threshold: float = 60.0,
        max_restarts: int = 3,
    ) -> None:
        self.worker_fn = worker_fn
        self.metrics = metrics
        self.heartbeat_name = heartbeat_name
        self.check_interval = check_interval
        self.stall_threshold = stall_threshold
        self.max_restarts = max_restarts

        self._restart_count = 0
        self._worker_thread: Optional[threading.Thread] = None
        self._monitor_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    def start(self) -> None:
        """Start the worker and the watchdog monitor."""
        self._start_worker()
        self._monitor_thread = threading.Thread(target=self._monitor, daemon=True)
        self._monitor_thread.start()

    def _start_worker(self) -> None:
        thread = threading.Thread(target=self.worker_fn, daemon=True)
        thread.start()
        self._worker_thread = thread
        logger.info("worker started by watchdog")

    def _monitor(self) -> None:
        while True:
            time.sleep(self.check_interval)
            last = self.metrics.get_last_heartbeat(self.heartbeat_name)
            stalled = time.time() - last > self.stall_threshold
            alive = self._worker_thread.is_alive() if self._worker_thread else False
            if stalled or not alive:
                self.metrics.record_counter("watchdog_restarts")
                logger.warning("worker stalled; restarting")
                self._restart_count += 1
                self._start_worker()
                if self._restart_count >= self.max_restarts:
                    self.metrics.record_counter("watchdog_alerts")
                    logger.error("worker repeatedly stalled; alerting")
                    self._restart_count = 0


__all__ = ["WorkerWatchdog"]
