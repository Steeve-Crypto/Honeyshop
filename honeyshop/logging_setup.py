"""Structured logging setup for Honeyshop."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class JSONFormatter(logging.Formatter):
    """Emit one JSON object per log line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Attach extra fields if present (optional: decoy, trap)
        for key in ("service", "src_ip", "src_port", "event", "data", "decoy", "trap"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = "logs/honeyshop.jsonl",
    also_console: bool = True,
) -> None:
    """Configure root honeyshop logger with optional JSON file output."""
    root = logging.getLogger("honeyshop")
    root.handlers.clear()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    if also_console:
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        root.addHandler(console)

    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(path, encoding="utf-8")
        fh.setFormatter(JSONFormatter())
        root.addHandler(fh)

    # Quiet noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
