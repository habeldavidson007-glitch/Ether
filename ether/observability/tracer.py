"""
Performance Tracing for Ether AI
Provides distributed tracing with span hierarchy and timing.
"""

import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from threading import local

from .logger import StructuredLogger

_thread_spans = local()


@dataclass
class TraceSpan:
    """Represents a single span in a trace."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def duration_ms(self) -> float:
        """Calculate duration in milliseconds."""
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time) * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary for export."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": round(self.duration_ms, 2),
            "tags": self.tags,
            "logs": self.logs
        }


class PerformanceTracer:
    """
    Distributed performance tracer with span hierarchy.
    """

    def __init__(self, logger: Optional[StructuredLogger] = None):
        self.logger = logger or StructuredLogger("ether.tracer")
        self._active_spans: Dict[str, TraceSpan] = {}
        self._completed_spans: List[TraceSpan] = []
        self._max_completed_spans = 1000

    def start_span(
        self,
        operation_name: str,
        parent_span: Optional[TraceSpan] = None,
        tags: Optional[Dict[str, Any]] = None
    ) -> TraceSpan:
        """Start a new trace span."""
        trace_id = parent_span.trace_id if parent_span else str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        parent_span_id = parent_span.span_id if parent_span else None
        
        span = TraceSpan(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            start_time=time.time(),
            tags=tags or {}
        )
        
        self._active_spans[span_id] = span
        
        # Store in thread-local for easy access
        if not hasattr(_thread_spans, 'stack'):
            _thread_spans.stack = []
        _thread_spans.stack.append(span)
        
        self.logger.debug(
            f"Span started: {operation_name}",
            span_id=span_id,
            trace_id=trace_id,
            operation="span_start"
        )
        
        return span

    def end_span(self, span: TraceSpan, tags: Optional[Dict[str, Any]] = None):
        """End a trace span."""
        span.end_time = time.time()
        
        if tags:
            span.tags.update(tags)
        
        if span.span_id in self._active_spans:
            del self._active_spans[span.span_id]
        
        # Remove from thread-local stack
        if hasattr(_thread_spans, 'stack') and _thread_spans.stack:
            try:
                _thread_spans.stack.remove(span)
            except ValueError:
                pass
        
        # Store completed span
        self._completed_spans.append(span)
        
        # Limit stored spans
        if len(self._completed_spans) > self._max_completed_spans:
            self._completed_spans = self._completed_spans[-self._max_completed_spans:]
        
        self.logger.log_performance(
            operation=span.operation_name,
            duration_ms=span.duration_ms,
            success=True,
            trace_id=span.trace_id,
            span_id=span.span_id
        )

    @contextmanager
    def trace(self, operation_name: str, tags: Optional[Dict[str, Any]] = None):
        """Context manager for automatic span lifecycle."""
        parent_span = None
        if hasattr(_thread_spans, 'stack') and _thread_spans.stack:
            parent_span = _thread_spans.stack[-1]
        
        span = self.start_span(operation_name, parent_span, tags)
        try:
            yield span
        except Exception as e:
            span.tags["error"] = str(e)
            span.tags["error_type"] = type(e).__name__
            self.logger.error(
                f"Span failed: {operation_name}",
                error=str(e),
                span_id=span.span_id
            )
            raise
        finally:
            self.end_span(span)

    def get_active_span(self) -> Optional[TraceSpan]:
        """Get the current active span from thread context."""
        if hasattr(_thread_spans, 'stack') and _thread_spans.stack:
            return _thread_spans.stack[-1]
        return None

    def get_completed_spans(self, trace_id: Optional[str] = None) -> List[TraceSpan]:
        """Get completed spans, optionally filtered by trace ID."""
        if trace_id:
            return [s for s in self._completed_spans if s.trace_id == trace_id]
        return self._completed_spans.copy()

    def export_spans(self, trace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Export spans as dictionaries for external systems."""
        spans = self.get_completed_spans(trace_id)
        return [span.to_dict() for span in spans]
