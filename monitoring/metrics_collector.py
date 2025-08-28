"""
Metrics - A1 Agentic System

Performance metrics collection and monitoring system.
Track success rates, iteration counts, and performance metrics.
"""

import time
import threading
from typing import Dict, Any, List
from collections import defaultdict, deque
from dataclasses import dataclass
import logging
import queue

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Single metric data point"""

    timestamp: float
    value: float
    tags: Dict[str, str]


class MetricsCollector:
    """
    Performance metrics collector.

    Collects and aggregates performance metrics for monitoring
    and optimization of the A1 system.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize metrics collector.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.enabled = config.get("ENABLE_METRICS", True)

        if not self.enabled:
            return

        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = defaultdict(float)

        self.lock = threading.Lock()

        self.start_time = time.time()

        # Background threads spawned by the collector (heartbeats, queue monitors)
        self._threads: List[threading.Thread] = []

    def record_execution(self, result):
        """Record execution metrics from result."""
        if not self.enabled:
            return

        with self.lock:
            timestamp = time.time()

            self.record_gauge(
                "execution_time",
                result.execution_time,
                {
                    "contract": result.contract_address,
                    "network": result.network,
                    "success": str(result.success),
                },
            )

            self.record_counter("contracts_processed")
            if result.success:
                self.record_counter("successful_executions")

            self.record_gauge(
                "exploits_found",
                result.exploits_found,
                {"contract": result.contract_address},
            )

            self.record_gauge(
                "profit_potential",
                result.total_profit_potential,
                {"contract": result.contract_address},
            )

    def record_counter(self, name: str, value: int = 1, tags: Dict[str, str] = None):
        """Record counter metric."""
        if not self.enabled:
            return

        with self.lock:
            self.counters[name] += value

    def record_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record gauge metric."""
        if not self.enabled:
            return

        with self.lock:
            self.gauges[name] = value
            self.metrics[name].append(
                MetricPoint(timestamp=time.time(), value=value, tags=tags or {})
            )

    # ------------------------------------------------------------------
    # Heartbeat and queue depth helpers
    # ------------------------------------------------------------------

    def record_heartbeat(self, name: str) -> None:
        """Record a heartbeat timestamp for a component."""
        if not self.enabled:
            return
        self.record_gauge(f"heartbeat_{name}", time.time())

    def get_last_heartbeat(self, name: str) -> float:
        """Get the most recent heartbeat timestamp."""
        if not self.enabled:
            return 0.0
        with self.lock:
            return self.gauges.get(f"heartbeat_{name}", 0.0)

    def start_heartbeat(self, name: str, interval: float = 30.0) -> None:
        """Start a background thread that periodically records heartbeats."""
        if not self.enabled:
            return

        def _beat() -> None:
            while True:
                try:
                    self.record_heartbeat(name)
                except Exception:  # pragma: no cover - defensive
                    logger.exception("Failed to record heartbeat for %s", name)
                time.sleep(interval)

        thread = threading.Thread(target=_beat, daemon=True)
        thread.start()
        self._threads.append(thread)

    def record_queue_depth(self, queue_name: str, depth: int) -> None:
        """Record queue depth as a gauge."""
        if not self.enabled:
            return
        self.record_gauge(f"queue_{queue_name}_depth", depth)

    def monitor_queue(
        self, q: queue.Queue, queue_name: str, interval: float = 5.0
    ) -> None:
        """Monitor a ``queue.Queue`` and publish its depth periodically."""
        if not self.enabled:
            return

        def _monitor() -> None:
            while True:
                try:
                    depth = q.qsize()
                except Exception:  # pragma: no cover - best effort
                    depth = 0
                self.record_queue_depth(queue_name, depth)
                time.sleep(interval)

        thread = threading.Thread(target=_monitor, daemon=True)
        thread.start()
        self._threads.append(thread)

    def record_iteration_metrics(
        self, iteration: int, success: bool, execution_time: float, exploits_found: int
    ):
        """Record metrics for agent iterations to track diminishing returns."""
        if not self.enabled:
            return

        with self.lock:
            self.record_counter(f"iteration_{iteration}_attempts")
            if success:
                self.record_counter(f"iteration_{iteration}_successes")

            self.record_gauge(f"iteration_{iteration}_execution_time", execution_time)
            self.record_gauge(f"iteration_{iteration}_exploits", exploits_found)

            if iteration > 1:
                improvement_key = f"iteration_{iteration}_improvement"
                self.record_gauge(improvement_key, exploits_found)

    def get_iteration_performance(self) -> Dict[str, Any]:
        """Get iteration performance metrics to track diminishing returns."""
        if not self.enabled:
            return {}

        with self.lock:
            iteration_stats = {}
            for i in range(1, 6):  # 5-iteration budget
                attempts = self.counters.get(f"iteration_{i}_attempts", 0)
                successes = self.counters.get(f"iteration_{i}_successes", 0)
                success_rate = successes / max(attempts, 1)

                iteration_stats[f"iteration_{i}"] = {
                    "attempts": attempts,
                    "successes": successes,
                    "success_rate": success_rate,
                    "avg_execution_time": self.gauges.get(
                        f"iteration_{i}_execution_time", 0
                    ),
                    "avg_exploits": self.gauges.get(f"iteration_{i}_exploits", 0),
                }

            return iteration_stats

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        if not self.enabled:
            return {}

        with self.lock:
            total_attempts = self.counters.get("contracts_processed", 0)
            total_successes = self.counters.get("successful_executions", 0)
            overall_success_rate = total_successes / max(total_attempts, 1)

            avg_execution_time = 0
            avg_exploits = 0
            avg_profit = 0

            if self.metrics["execution_time"]:
                avg_execution_time = sum(
                    p.value for p in self.metrics["execution_time"]
                ) / len(self.metrics["execution_time"])

            if self.metrics["exploits_found"]:
                avg_exploits = sum(
                    p.value for p in self.metrics["exploits_found"]
                ) / len(self.metrics["exploits_found"])

            if self.metrics["profit_potential"]:
                avg_profit = sum(
                    p.value for p in self.metrics["profit_potential"]
                ) / len(self.metrics["profit_potential"])

            return {
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "uptime": time.time() - self.start_time,
                "metrics_count": sum(len(m) for m in self.metrics.values()),
                "performance": {
                    "overall_success_rate": overall_success_rate,
                    "avg_execution_time": avg_execution_time,
                    "avg_exploits_per_contract": avg_exploits,
                    "avg_profit_potential": avg_profit,
                },
                "iteration_performance": self.get_iteration_performance(),
            }
