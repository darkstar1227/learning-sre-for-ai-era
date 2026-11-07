"""Structured JSON logging setup."""

import json
import logging
import sys
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """Format log as single-line JSON with request_id correlation."""

    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
        }

        # Include request_id if available
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id

        # Include other fields from LogRecord if they're custom
        if hasattr(record, "event"):
            log_obj["event"] = record.event
        if hasattr(record, "dependency"):
            log_obj["dependency"] = record.dependency
        if hasattr(record, "error_class"):
            log_obj["error_class"] = record.error_class
        if hasattr(record, "retry_count"):
            log_obj["retry_count"] = record.retry_count
        if hasattr(record, "duration_ms"):
            log_obj["duration_ms"] = record.duration_ms

        return json.dumps(log_obj, ensure_ascii=False)


def setup_logging():
    """Configure structured JSON logging to stdout.

    Idempotent: safe to call multiple times, only adds handler once.
    """
    logger = logging.getLogger("app")
    logger.setLevel(logging.INFO)

    # Check if we already have a JSONFormatter handler to avoid duplicates
    for handler in logger.handlers:
        if isinstance(handler.formatter, JSONFormatter):
            return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    logger.addHandler(handler)
    return logger
