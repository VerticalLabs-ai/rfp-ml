"""
Centralized logging configuration for the RFP ML system.

This module should be imported and setup_logging() called once at application
startup, not in individual module constructors.

Usage:
    from src.config.logging_config import setup_logging
    setup_logging()  # Call once at startup
"""
import logging
import sys
from pathlib import Path
from typing import Optional


# Track if logging has been configured
_logging_configured = False


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    format_string: Optional[str] = None
) -> None:
    """
    Configure logging for the entire application.

    Should be called once at application startup. Subsequent calls are no-ops.

    Args:
        level: Logging level (default: INFO)
        log_file: Optional file path to write logs to
        format_string: Custom format string (uses sensible default if not provided)
    """
    global _logging_configured

    if _logging_configured:
        return

    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    handlers: list[logging.Handler] = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(format_string))
    handlers.append(console_handler)

    # File handler (optional)
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(format_string))
        handlers.append(file_handler)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add new handlers
    for handler in handlers:
        root_logger.addHandler(handler)

    _logging_configured = True
    logging.info("Logging configured successfully")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    This ensures logging is configured before returning a logger.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    if not _logging_configured:
        setup_logging()
    return logging.getLogger(name)


def reset_logging() -> None:
    """
    Reset logging configuration. Primarily for testing purposes.
    """
    global _logging_configured
    _logging_configured = False

    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
