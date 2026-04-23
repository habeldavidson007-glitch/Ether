"""
Metrics Collection for Ether AI
Provides request metrics, performance statistics, and aggregations.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from threading import Lock
import statistics


@dataclass
class RequestMetrics:
    """Metrics for a single request or operation."""
    operation: str
    start_time: float
    end_time: Optional[float] = None
    status: str = "pending"  # pending, success, error
    error_type: Optional[str] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration_ms(self) -> float:
        """Calculate duration in milliseconds."""
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time) * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "operation": self.operation,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": round(self.duration_ms, 2),
            "status": self.status,
            "error_type": self.error_type,
            "tags": self.tags
        }


class MetricsCollector:
    """
    Collects and aggregates metrics for performance analysis.
    Thread-safe implementation with statistical aggregations.
    """

    def __init__(self, max_samples: int = 10000):
        self.max_samples = max_samples
        self._lock = Lock()
        self._metrics: Dict[str, List[RequestMetrics]] = defaultdict(list)
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}

    def record_start(self, operation: str, tags: Optional[Dict[str, Any]] = None) -> RequestMetrics:
        """Record the start of an operation."""
        metric = RequestMetrics(
            operation=operation,
            start_time=time.time(),
            tags=tags or {}
        )
        
        with self._lock:
            self._counters[f"{operation}.started"] += 1
        
        return metric

    def record_end(
        self,
        metric: RequestMetrics,
        status: str = "success",
        error_type: Optional[str] = None
    ):
        """Record the end of an operation."""
        metric.end_time = time.time()
        metric.status = status
        metric.error_type = error_type
        
        with self._lock:
            self._metrics[metric.operation].append(metric)
            
            # Limit stored metrics
            if len(self._metrics[metric.operation]) > self.max_samples:
                self._metrics[metric.operation] = \
                    self._metrics[metric.operation][-self.max_samples:]
            
            # Update counters
            if status == "success":
                self._counters[f"{metric.operation}.success"] += 1
            else:
                self._counters[f"{metric.operation}.error"] += 1

    def record_counter(self, name: str, value: int = 1):
        """Increment a counter metric."""
        with self._lock:
            self._counters[name] += value

    def record_gauge(self, name: str, value: float):
        """Set a gauge metric."""
        with self._lock:
            self._gauges[name] = value

    def get_operation_stats(self, operation: str) -> Dict[str, Any]:
        """Get statistical summary for an operation."""
        with self._lock:
            metrics = self._metrics.get(operation, [])
        
        if not metrics:
            return {
                "operation": operation,
                "count": 0,
                "min_ms": 0,
                "max_ms": 0,
                "avg_ms": 0,
                "median_ms": 0,
                "p95_ms": 0,
                "p99_ms": 0,
                "success_rate": 0.0
            }
        
        durations = [m.duration_ms for m in metrics if m.end_time]
        success_count = sum(1 for m in metrics if m.status == "success")
        
        return {
            "operation": operation,
            "count": len(metrics),
            "min_ms": round(min(durations), 2) if durations else 0,
            "max_ms": round(max(durations), 2) if durations else 0,
            "avg_ms": round(statistics.mean(durations), 2) if durations else 0,
            "median_ms": round(statistics.median(durations), 2) if durations else 0,
            "p95_ms": round(self._percentile(durations, 95), 2) if durations else 0,
            "p99_ms": round(self._percentile(durations, 99), 2) if durations else 0,
            "success_rate": round(success_count / len(metrics) * 100, 2) if metrics else 0.0
        }

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile value."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all operations."""
        with self._lock:
            operations = list(self._metrics.keys())
        
        return {op: self.get_operation_stats(op) for op in operations}

    def get_counters(self) -> Dict[str, int]:
        """Get all counter metrics."""
        with self._lock:
            return dict(self._counters)

    def get_gauges(self) -> Dict[str, float]:
        """Get all gauge metrics."""
        with self._lock:
            return dict(self._gauges)

    def export_metrics(self) -> Dict[str, Any]:
        """Export all metrics for external systems."""
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "statistics": self.get_all_stats(),
                "timestamp": time.time()
            }

    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self._metrics.clear()
            self._counters.clear()
            self._gauges.clear()
