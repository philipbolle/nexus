"""
NEXUS Centralized Logging Configuration

Provides structured logging with JSON format for production,
with configurable log levels and output destinations.
"""

import json
import logging
import logging.config
import sys
from datetime import datetime
from typing import Any, Dict, Optional
import os

from .config import settings


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging in production."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        # Add request context if available
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "endpoint"):
            log_data["endpoint"] = record.endpoint
        if hasattr(record, "method"):
            log_data["method"] = record.method
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id

        return json.dumps(log_data, default=str)


class ConsoleFormatter(logging.Formatter):
    """Human-readable formatter for development."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record for console output."""
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        level = record.levelname.ljust(8)
        logger = record.name

        # Color codes for different levels
        colors = {
            "DEBUG": "\033[36m",  # Cyan
            "INFO": "\033[32m",   # Green
            "WARNING": "\033[33m", # Yellow
            "ERROR": "\033[31m",   # Red
            "CRITICAL": "\033[35m", # Magenta
        }
        reset = "\033[0m"

        color = colors.get(record.levelname, "")

        # Base format
        message = f"{timestamp} {color}{level}{reset} [{logger}] {record.getMessage()}"

        # Add exception info if present
        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"

        # Add extra fields if present
        if hasattr(record, "extra") and record.extra:
            message += f" | {record.extra}"

        return message


def get_logging_config() -> Dict[str, Any]:
    """Get logging configuration based on environment."""

    # Default log level from settings or environment
    log_level = getattr(settings, "log_level", "INFO").upper()

    # Determine formatter based on environment
    is_production = os.getenv("NEXUS_ENV", "development") == "production"

    if is_production:
        formatter = "json"
        formatter_config = {
            "()": "app.logging_config.StructuredFormatter",
        }
    else:
        formatter = "console"
        formatter_config = {
            "()": "app.logging_config.ConsoleFormatter",
        }

    # Log file configuration
    log_file = getattr(settings, "log_file", None)

    handlers = {
        "console": {
            "class": "logging.StreamHandler",
            "level": log_level,
            "formatter": formatter,
            "stream": sys.stdout,
        }
    }

    # Add file handler if log_file is configured
    if log_file:
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "formatter": formatter,
            "filename": log_file,
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf8",
        }

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": formatter_config,
            "console": formatter_config,
        },
        "handlers": handlers,
        "loggers": {
            # Root logger
            "": {
                "handlers": list(handlers.keys()),
                "level": log_level,
                "propagate": True,
            },
            # FastAPI logger
            "uvicorn": {
                "handlers": list(handlers.keys()),
                "level": log_level,
                "propagate": False,
            },
            # Application loggers
            "app": {
                "handlers": list(handlers.keys()),
                "level": log_level,
                "propagate": False,
            },
            # Database logger
            "asyncpg": {
                "handlers": list(handlers.keys()),
                "level": "WARNING",  # Reduce noise from database
                "propagate": False,
            },
            # AI providers logger
            "httpx": {
                "handlers": list(handlers.keys()),
                "level": "WARNING",  # Reduce noise from HTTP requests
                "propagate": False,
            },
        },
    }


def setup_logging() -> None:
    """Setup logging configuration."""
    config = get_logging_config()
    logging.config.dictConfig(config)

    logger = logging.getLogger(__name__)

    # Log configuration summary
    is_production = os.getenv("NEXUS_ENV", "development") == "production"
    log_level = getattr(settings, "log_level", "INFO").upper()
    log_file = getattr(settings, "log_file", None)

    logger.info(
        "Logging configured",
        extra={
            "environment": "production" if is_production else "development",
            "log_level": log_level,
            "formatter": "json" if is_production else "console",
            "log_file": log_file,
        }
    )


def get_logger(name: str) -> logging.Logger:
    """Get logger with structured logging support."""
    logger = logging.getLogger(name)

    # Add adapter for structured logging
    class StructuredLoggerAdapter(logging.LoggerAdapter):
        def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
            extra = self.extra.copy() if self.extra else {}
            extra.update(kwargs.get("extra", {}))
            kwargs["extra"] = extra
            return msg, kwargs

    return StructuredLoggerAdapter(logger, {})


# Global logger instance
logger = get_logger(__name__)


def log_request(
    logger: logging.Logger,
    request_id: str,
    endpoint: str,
    method: str,
    user_id: Optional[str] = None,
    **kwargs
) -> None:
    """Log HTTP request with structured context."""
    extra = {
        "request_id": request_id,
        "endpoint": endpoint,
        "method": method,
        **kwargs,
    }
    if user_id:
        extra["user_id"] = user_id

    logger.info(f"Request: {method} {endpoint}", extra=extra)


def log_response(
    logger: logging.Logger,
    request_id: str,
    endpoint: str,
    method: str,
    status_code: int,
    duration_ms: float,
    user_id: Optional[str] = None,
    **kwargs
) -> None:
    """Log HTTP response with structured context."""
    extra = {
        "request_id": request_id,
        "endpoint": endpoint,
        "method": method,
        "status_code": status_code,
        "duration_ms": duration_ms,
        **kwargs,
    }
    if user_id:
        extra["user_id"] = user_id

    log_level = logging.INFO if status_code < 400 else logging.WARNING
    logger.log(
        log_level,
        f"Response: {method} {endpoint} -> {status_code} ({duration_ms:.1f}ms)",
        extra=extra,
    )


def log_error(
    logger: logging.Logger,
    error: Exception,
    request_id: Optional[str] = None,
    endpoint: Optional[str] = None,
    method: Optional[str] = None,
    user_id: Optional[str] = None,
    **kwargs
) -> None:
    """Log error with structured context."""
    extra = {
        "error_type": error.__class__.__name__,
        "error_message": str(error),
        **kwargs,
    }
    if request_id:
        extra["request_id"] = request_id
    if endpoint:
        extra["endpoint"] = endpoint
    if method:
        extra["method"] = method
    if user_id:
        extra["user_id"] = user_id

    logger.error(f"Error: {error.__class__.__name__}: {error}", extra=extra, exc_info=True)