"""JSONL interaction schema stability tests."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from honeyshop.logging_setup import JSONFormatter, setup_logging
from honeyshop.services.base import BaseService


REQUIRED_FIELDS = {
    "timestamp",
    "level",
    "logger",
    "message",
    "service",
    "src_ip",
    "src_port",
    "event",
    "data",
}


def test_json_formatter_core_fields():
    fmt = JSONFormatter()
    record = logging.LogRecord(
        name="honeyshop.services",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="interaction",
        args=(),
        exc_info=None,
    )
    record.service = "ssh"
    record.src_ip = "203.0.113.10"
    record.src_port = 4444
    record.event = "banner_sent"
    record.data = "SSH-2.0-test"

    payload = json.loads(fmt.format(record))
    assert REQUIRED_FIELDS.issubset(payload.keys())
    assert payload["service"] == "ssh"
    assert payload["src_ip"] == "203.0.113.10"
    assert payload["src_port"] == 4444
    assert payload["event"] == "banner_sent"
    assert payload["data"] == "SSH-2.0-test"
    assert "timestamp" in payload and payload["timestamp"]


def test_json_formatter_optional_decoy_and_trap():
    fmt = JSONFormatter()
    record = logging.LogRecord(
        name="honeyshop.services",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="interaction",
        args=(),
        exc_info=None,
    )
    record.service = "http"
    record.src_ip = "198.51.100.9"
    record.src_port = 9000
    record.event = "http_request"
    record.data = "GET /"
    record.decoy = True
    record.trap = "rust"

    payload = json.loads(fmt.format(record))
    # Optional fields must pass through when present (schema-compatible)
    assert payload.get("decoy") is True
    assert payload.get("trap") == "rust"


def test_log_interaction_writes_schema(tmp_path: Path):
    log_file = tmp_path / "honeyshop.jsonl"
    setup_logging(level="INFO", log_file=str(log_file), also_console=False)

    class Tiny(BaseService):
        def handle_client(self, client, addr):
            pass

    svc = Tiny(name="ssh")
    svc.log_interaction(("10.0.0.8", 12345), "banner_sent", "hello")

    # Flush handlers
    for h in logging.getLogger("honeyshop").handlers:
        h.flush()

    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert lines, "expected JSONL output"
    row = json.loads(lines[-1])
    for key in REQUIRED_FIELDS:
        assert key in row, f"missing field {key}"
