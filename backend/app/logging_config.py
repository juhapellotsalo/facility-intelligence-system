"""Logging configuration for Facility Intelligence System."""

import logging
from datetime import datetime
from pathlib import Path

from app.config import LOG_LEVEL


def setup_logging() -> None:
    """Configure logging with file and console handlers."""
    # Create logs directory at project root
    logs_dir = Path(__file__).parent.parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Log file with date
    log_file = logs_dir / f"facility-{datetime.now().strftime('%Y-%m-%d')}.log"

    # Format: timestamp - level - logger - message
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    # Console handler (less verbose)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL))
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Quiet down noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    # Our app loggers at INFO level
    logging.getLogger("app").setLevel(logging.INFO)
    logging.getLogger("app.agent").setLevel(logging.INFO)
    logging.getLogger("app.routes").setLevel(logging.INFO)

    logging.info(f"Logging initialized - file: {log_file}")
