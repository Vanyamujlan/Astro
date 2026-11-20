"""Centralized logging configuration with Loguru and secret redaction."""

import logging
import sys
from typing import Any

from loguru import logger

from app.utils.sanitizers import sanitize_secrets


class _InterceptHandler(logging.Handler):
    """Route standard library logging records into Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame = sys._getframe(6)
        depth = 6
        while frame and frame.f_code.co_filename == logging.__file__:
            if frame.f_back is None:
                break
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level,
            record.getMessage(),
        )


def _redact_record_patcher(record: dict[str, Any]) -> None:
    """Sanitize log message text before formatting so secrets never leak."""
    message = record.get("message")
    if isinstance(message, str):
        record["message"] = sanitize_secrets(message)


def setup_logging(log_level: str = "INFO", environment: str = "development") -> None:
    """Configure Loguru sinks and bridge standard library loggers."""
    logger.remove()
    logger.configure(patcher=_redact_record_patcher)

    is_dev = environment == "development"
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    logger.add(
        sys.stderr,
        level=log_level.upper(),
        format=log_format,
        colorize=is_dev,
        backtrace=is_dev,
        diagnose=False,  # Never expose local variable values in tracebacks
    )

    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)

    # Reduce noisy HTTP polling logs from httpx / telegram internals unless DEBUG
    if log_level.upper() != "DEBUG":
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
