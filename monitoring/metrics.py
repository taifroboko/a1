"""
Metrics - A1 Agentic System

Performance metrics collection and monitoring system.
Re-exports the MetricsCollector for the expected module structure.
"""

from .metrics_collector import MetricsCollector, MetricPoint

__all__ = ['MetricsCollector', 'MetricPoint']
