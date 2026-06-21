"""Centralized logging configuration for the Enterprise RAG application."""
import logging
import sys


def configure_logging(level: int = logging.INFO) -> None:
    """Configure root logger with a consistent format. Call once at startup."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,  # override any prior basicConfig calls
    )
