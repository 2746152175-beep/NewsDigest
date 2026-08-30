"""Logging setup writing daily-rotated logs to the configured directory."""

import logging
from logging.handlers import TimedRotatingFileHandler

from src.config_loader import resolve_path

_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def setup_logging(config: dict) -> None:
    """Configure root logging from config.yaml (log.dir and log.level)."""
    log_cfg = config.get("log") or {}
    log_dir = resolve_path(log_cfg.get("dir") or "logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    level_name = str(log_cfg.get("level") or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)

    if not root.handlers:
        file_handler = TimedRotatingFileHandler(
            log_dir / "news-agent.log",
            when="midnight",
            backupCount=7,
            encoding="utf-8",
        )
        file_handler.setFormatter(logging.Formatter(_FORMAT))
        root.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(_FORMAT))
        root.addHandler(console_handler)
