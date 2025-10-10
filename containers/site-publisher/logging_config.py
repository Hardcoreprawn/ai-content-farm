"""
Secure logging configuration for site-publisher.

Provides structured JSON logging with sensitive data filtering.
"""

import logging
import re
import sys
from typing import Any


class SensitiveDataFilter(logging.Filter):
    """Filter sensitive data from logs."""

    SENSITIVE_PATTERNS = [
        "password",
        "secret",
        "token",
        "key",
        "credential",
        "authorization",
        "connection_string",
        "accountkey",
        "sas",
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter out log records containing sensitive data."""
        # Check message
        if hasattr(record, "msg"):
            msg_lower = str(record.msg).lower()
            if any(pattern in msg_lower for pattern in self.SENSITIVE_PATTERNS):
                record.msg = "[REDACTED - Sensitive data filtered]"

        # Check args
        if hasattr(record, "args") and record.args:
            safe_args = []
            for arg in record.args:
                arg_str = str(arg).lower()
                if any(pattern in arg_str for pattern in self.SENSITIVE_PATTERNS):
                    safe_args.append("[REDACTED]")
                else:
                    safe_args.append(arg)
            record.args = tuple(safe_args)

        return True


def configure_secure_logging(log_level: str = "INFO") -> None:
    """
    Configure secure logging for site-publisher.

    Features:
    - No sensitive data in logs
    - Structured JSON format (for Application Insights)
    - Appropriate log levels
    - No file path disclosure

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Remove existing handlers
    logger.handlers = []

    # Console handler with formatting
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    # Structured format (Azure-friendly)
    formatter = logging.Formatter(
        '{"time": "%(asctime)s", "level": "%(levelname)s", '
        '"logger": "%(name)s", "message": "%(message)s"}'
    )
    handler.setFormatter(formatter)

    # Add sensitive data filter
    handler.addFilter(SensitiveDataFilter())

    logger.addHandler(handler)

    # Suppress noisy Azure SDK logs
    logging.getLogger("azure").setLevel(logging.WARNING)
    logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(
        logging.WARNING
    )
    logging.getLogger("azure.identity").setLevel(logging.WARNING)
