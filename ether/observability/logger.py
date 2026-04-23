"""
Structured Logging for Ether AI
Provides JSON-formatted logs with context, levels, and correlation IDs.
"""

import json
import logging
import sys
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from threading import local

_thread_context = local()


class StructuredLogger:
    """
    JSON-structured logger with correlation ID support for distributed tracing.
    """

    def __init__(self, name: str = "ether", level: int = logging.INFO):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Remove existing handlers to avoid duplicates
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter('%(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        self._correlation_id: Optional[str] = None

    def set_correlation_id(self, correlation_id: Optional[str] = None):
        """Set or generate a correlation ID for request tracing."""
        self._correlation_id = correlation_id or str(uuid.uuid4())
        _thread_context.correlation_id = self._correlation_id

    def get_correlation_id(self) -> Optional[str]:
        """Get current correlation ID from thread context."""
        return getattr(_thread_context, 'correlation_id', self._correlation_id)

    def _log(self, level: str, message: str, **kwargs):
        """Internal method to create structured log entry."""
        log_entry: Dict[str, Any] = {
            "timestamp": self.now_utc(),
            "level": level,
            "logger": self.name,
            "message": message,
            "correlation_id": self.get_correlation_id(),
            **kwargs
        }
        
        # Add extra context if provided
        if "context" in kwargs:
            log_entry["context"] = kwargs.pop("context")
        
        log_line = json.dumps(log_entry, default=str)
        
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(log_line)

    def info(self, message: str, **kwargs):
        """Log info level message."""
        self._log("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning level message."""
        self._log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error level message."""
        self._log("ERROR", message, **kwargs)

    def debug(self, message: str, **kwargs):
        """Log debug level message."""
        self._log("DEBUG", message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical level message."""
        self._log("CRITICAL", message, **kwargs)

    def log_event(self, event_type: str, event_data: Dict[str, Any]):
        """Log a structured event."""
        self.info(
            f"Event: {event_type}",
            event_type=event_type,
            event_data=event_data
        )

    def log_performance(self, operation: str, duration_ms: float, success: bool = True, **kwargs):
        """Log performance metrics for an operation."""
        self.info(
            f"Performance: {operation}",
            operation=operation,
            duration_ms=round(duration_ms, 2),
            success=success,
            metric_type="performance",
            **kwargs
        )

    @staticmethod
    def now_utc() -> str:
        """Get current UTC timestamp in ISO format."""
        from datetime import timezone
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
