"""Minimal HTTP API for the Honeyshop UI. python -m honeyshop.api_server"""

from __future__ import annotations

import json
import os
import socket
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

from .alerts import AlertConfig, Notifier
from .decoy import DecoyLogGenerator
from .monitor import EbpfWatcher

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = Path(os.environ.get("HONEYSHOP_LOG_FILE", str(ROOT / "logs" / "honeyshop.jsonl")))
DECOY_DIR = Path(os.environ.get("HONEYSHOP_DECOY_DIR", str(ROOT / "logs" / "decoy")))
RUNTIME_CONFIG = Path(
    os.environ.get("HONEYSHOP_RUNTIME_CONFIG", str(ROOT / "config" / "runtime.json"))
)
HOST = os.environ.get("HONEYSHOP_API_HOST", "127.0.0.1")
PORT = int(os.environ.get("HONEYSHOP_API_PORT", "8787"))
WS_PORT = int(os.environ.get("HONEYSHOP_WS_PORT", "8788"))
DEFAULT_PORTS = {"ssh": 2222, "http": 8080, "ftp": 2121}

_lock = threading.Lock()
_decoy: Optional[DecoyLogGenerator] = None
_runtime: dict[str, Any] = {}


def _load_runtime() -> dict[str, Any]:
    global _runtime
    if RUNTIME_CONFIG.exists():
        try:
            _runtime = json.loads(RUNTIME_CONFIG.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            _runtime = {}
    else:
        _runtime = {}
    return _runtime


def _save_runtime() -> None:
    RUNTIME_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME_CONFIG.write_text(json.dumps(_runtime, indent=2), encoding="utf-8")


def _apply_runtime_to_env() -> None:
    mapping = {
        "slack_webhook": "HONEYSHOP_SLACK_WEBHOOK",
        "smtp_host": "HONEYSHOP_SMTP_HOST",
        "smtp_port": "HONEYSHOP_SMTP_PORT",
        "smtp_user": "HONEYSHOP_SMTP_USER",
        "smtp_password": "HONEYSHOP_SMTP_PASSWORD",
        "email_from": "HONEYSHOP_EMAIL_FROM",
        "email_to": "HONEYSHOP_EMAIL_TO",
    }
    for key, env in mapping.items():
        val = _runtime.get(key)
        if val is None or val == "":
            continue
        os.environ[env] = str(val)


def _read_jsonl(path: Path, limit: int = 100) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()[-limit:]
    except OSError:
        return []
    out = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    out.reverse()
    return out


def _port_open(port: int, host: str = "127.0.0.1") -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.35):
            return True
    except OSError:
        return False


def _services() -> list[dict[str, Any]]:
    interactions = _read_jsonl(DEFAULT_LOG, limit=500)
    counts = {"ssh": 0, "http": 0, "ftp": 0}
    for row in interactions:
        svc = str(row.get("service") or "").lower()
        if svc in counts:
            counts[svc] += 1
    return [
        {"name": n, "port": p, "enabled": _port_open(p), "hits": counts[n]}
        for n, p in DEFAULT_PORTS.items()
    ]


def _alerts_from_logs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    alerts = []
    high_kw = ("wget", "curl", "mirai", "busybox", "/bin/bash", "base64", "shadow", "id_rsa")
    ip_counts: dict[str, int] = {}
    for row in rows:
        ip = str(row.get("src_ip") or "")
        if ip:
            ip_counts[ip] = ip_counts.get(ip, 0) + 1
        data = str(row.get("data") or "").lower()
        event = str(row.get("event") or "")
        if any(k in data for k in high_kw):
            alerts.append(
                {
                    "id": f"payload-{len(alerts)}",
                    "severity": "high",
                    "title": "Suspicious payload",
                    "detail": data[:160],
                    "time": row.get("timestamp") or "",
                }
            )
        if "login" in event:
            alerts.append(
                {
                    "id": f"login-{len(alerts)}",
                    "severity": "medium",
                    "title": "Login attempt",
                    "detail": f"{row.get('service', '?')} from {ip}",
                    "time": row.get("timestamp") or "",
                }
            )
        if row.get("service") == "ebpf" or event in ("exec", "open"):
            alerts.append(
                {
                    "id": f"ebpf-{len(alerts)}",
                    "severity": "medium",
                    "title": f"eBPF {event}",
                    "detail": data[:160],
                    "time": row.get("timestamp") or "",
                }
            )
    for ip, n in ip_counts.items():
        if n >= 8:
            alerts.append(
                {
                    "id": f"vol-{ip}",
                    "severity": "medium",
                    "title": "High volume source IP",
                    "detail": f"{ip} → {n} events",
                    "time": datetime.now(timezone.utc).isoformat(),
                }
            )
    seen, uniq = set(), []
    for a in alerts:
        key = (a["title"], a["detail"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(a)
    return uniq[:40]


def _decoy_running() -> bool:
    with _lock:
        return _decoy is not None and getattr(_decoy, "_running", False)


def _status() -> dict[str, Any]:
    rows = _read_jsonl(DEFAULT_LOG, limit=200)
    decoy_files = list(DECOY_DIR.glob("*.log")) if DECOY_DIR.exists() else []
    return {
        "ok": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "log_file": str(DEFAULT_LOG),
        "log_exists": DEFAULT_LOG.exists(),
        "interaction_count": len(rows),
        "decoy_dir": str(DECOY_DIR),
        "decoy_active": _decoy_running() or bool(decoy_files),
        "decoy_running": _decoy_running(),
        "decoy_files": [p.name for p in decoy_files],
        "alerts_configured": bool(
            os.environ.get("HONEYSHOP_SLACK_WEBHOOK") or os.environ.get("HONEYSHOP_EMAIL_TO")
        ),
        "stream_up": _port_open(WS_PORT),
    }


def _mask_secret(value: Optional[str]) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "••••••••"
    return value[:4] + "…" + value[-4:]


def _config_public() -> dict[str, Any]:
    cfg = AlertConfig.from_env()
    return {
        "slack_webhook": _mask_secret(cfg.slack_webhook),
        "slack_configured": bool(cfg.slack_webhook),
        "smtp_host": cfg.smtp_host or "",
        "smtp_port": cfg.smtp_port,
        "smtp_user": cfg.smtp_user or "",
        "smtp_password": "••••••••" if cfg.smtp_password else "",
        "smtp_configured": bool(cfg.smtp_host and cfg.email_to),
        "email_from": cfg.email_from or "",
        "email_to": cfg.email_to or "",
        "log_file": str(DEFAULT_LOG),
        "decoy_dir": str(DECOY_DIR),
        "ports": dict(DEFAULT_PORTS),
        "api_host": HOST,
        "api_port": PORT,
        "ws_port": WS_PORT,
    }


def _features() -> dict[str, Any]:
    try:
        ebpf_ok, ebpf_reason = EbpfWatcher.available()
    except Exception as e:  # noqa: BLE001 — geteuid missing on some platforms
        ebpf_ok, ebpf_reason = False, str(e)

    services = _services()
    any_listener = any(s["enabled"] for s in services)
    cfg = AlertConfig.from_env()
    return {
        "ok": True,
        "api": True,
        "stream": {
            "up": _port_open(WS_PORT),
            "url": f"ws://127.0.0.1:{WS_PORT}/ws/interactions",
            "cli": "python -m honeyshop.stream",
        },
        "engine": {
            "listeners_up": any_listener,
            "services": services,
            "cli": "python -m honeyshop",
            "note": "Service ports bind in the engine process, not the browser",
        },
        "rust_trap": {
            "cli": "cargo run --release -p honeyshop-trap -- crates/honeyshop-trap/config.example.toml",
            "note": "Optional hot path; same JSONL with trap: rust",
        },
        "decoy": {
            "controllable": True,
            "running": _decoy_running(),
            "dir": str(DECOY_DIR),
        },
        "alerts": {
            "slack": bool(cfg.slack_webhook),
            "email": bool(cfg.smtp_host and cfg.email_to),
            "enabled": bool(cfg.slack_webhook or (cfg.smtp_host and cfg.email_to)),
        },
        "ebpf": {
            "available": ebpf_ok,
            "reason": ebpf_reason,
            "ui_toggle": False,
            "cli": "sudo python -m honeyshop --ebpf",
            "note": "Needs root + bpftrace on the engine process; not UI-toggleable",
        },
        "limits": [
            "eBPF requires root + bpftrace on the engine process",
            "Binding privileged/service ports is host process only",
            "ELK deploy is separate (compose override)",
        ],
    }


def _norm(row: dict[str, Any]) -> dict[str, Any]:
    out = {
        "timestamp": row.get("timestamp") or "",
        "service": row.get("service") or "unknown",
        "src_ip": row.get("src_ip") or "",
        "src_port": row.get("src_port") or 0,
        "event": row.get("event") or row.get("message") or "",
        "data": row.get("data") or "",
        "decoy": bool(row.get("decoy")),
    }
    if row.get("trap"):
        out["trap"] = row.get("trap")
    return out


def _start_decoy() -> dict[str, Any]:
    global _decoy
    with _lock:
        if _decoy is not None and getattr(_decoy, "_running", False):
            return {"ok": True, "action": "start_decoy", "running": True, "message": "already running"}
        log_file = str(DEFAULT_LOG)
        _decoy = DecoyLogGenerator(output_dir=str(DECOY_DIR), also_jsonl=log_file)
        _decoy.start()
        return {"ok": True, "action": "start_decoy", "running": True, "decoy_dir": str(DECOY_DIR)}


def _stop_decoy() -> dict[str, Any]:
    global _decoy
    with _lock:
        if _decoy is None:
            return {"ok": True, "action": "stop_decoy", "running": False, "message": "not running"}
        _decoy.stop()
        _decoy = None
        return {"ok": True, "action": "stop_decoy", "running": False}


def _test_alert() -> dict[str, Any]:
    notifier = Notifier(AlertConfig.from_env())
    if not notifier.enabled:
        return {
            "ok": False,
            "action": "test_alert",
            "error": "No alert channel configured. Set Slack webhook or SMTP via Settings / env.",
        }
    title = "Honeyshop test alert"
    body = f"Control-plane test at {datetime.now(timezone.utc).isoformat()}"
    try:
        notifier.send(title, body, severity="low")
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "action": "test_alert", "error": str(e)}
    return {
        "ok": True,
        "action": "test_alert",
        "slack": bool(notifier.config.slack_webhook),
        "email": bool(notifier.config.smtp_host and notifier.config.email_to),
    }


def _update_config(body: dict[str, Any]) -> dict[str, Any]:
    allowed = (
        "slack_webhook",
        "smtp_host",
        "smtp_port",
        "smtp_user",
        "smtp_password",
        "email_from",
        "email_to",
    )
    changed = []
    for key in allowed:
        if key not in body:
            continue
        val = body[key]
        if val is None:
            continue
        # Ignore masked placeholders so save doesn't wipe secrets
        if isinstance(val, str) and ("…" in val or "••••" in val):
            continue
        if key == "smtp_port":
            try:
                val = int(val)
            except (TypeError, ValueError):
                continue
        _runtime[key] = val
        changed.append(key)
    _save_runtime()
    _apply_runtime_to_env()
    return {"ok": True, "changed": changed, "config": _config_public()}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        limit = int(parse_qs(parsed.query).get("limit", ["80"])[0])
        if path in ("/", "/api/health"):
            return self._json(200, {"ok": True})
        if path == "/api/status":
            return self._json(200, _status())
        if path == "/api/features":
            return self._json(200, _features())
        if path == "/api/config":
            return self._json(200, _config_public())
        if path == "/api/interactions":
            rows = [_norm(r) for r in _read_jsonl(DEFAULT_LOG, limit=limit)]
            return self._json(200, {"items": rows, "count": len(rows)})
        if path == "/api/services":
            return self._json(200, {"items": _services()})
        if path == "/api/alerts":
            return self._json(200, {"items": _alerts_from_logs(_read_jsonl(DEFAULT_LOG, limit=300))})
        if path == "/api/overview":
            rows = _read_jsonl(DEFAULT_LOG, limit=300)
            services = _services()
            ips: dict[str, int] = {}
            for r in rows:
                ip = r.get("src_ip") or ""
                if ip:
                    ips[ip] = ips.get(ip, 0) + 1
            return self._json(
                200,
                {
                    "services": services,
                    "alerts": _alerts_from_logs(rows)[:8],
                    "recent": [_norm(r) for r in rows[:12]],
                    "total_hits": sum(s["hits"] for s in services),
                    "unique_sources": len(ips),
                    "status": _status(),
                    "features": _features(),
                },
            )
        self._json(404, {"error": "not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        body = self._read_body()
        if path == "/api/config":
            return self._json(200, _update_config(body))
        if path == "/api/control":
            action = str(body.get("action") or "").strip()
            if action == "start_decoy":
                return self._json(200, _start_decoy())
            if action == "stop_decoy":
                return self._json(200, _stop_decoy())
            if action == "test_alert":
                result = _test_alert()
                return self._json(200 if result.get("ok") else 400, result)
            return self._json(
                400,
                {
                    "ok": False,
                    "error": "unknown action",
                    "allowed": ["start_decoy", "stop_decoy", "test_alert"],
                },
            )
        self._json(404, {"error": "not found"})


def main():
    _load_runtime()
    _apply_runtime_to_env()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Honeyshop API http://{HOST}:{PORT}")
    print("  GET  /api/{health,status,features,config,interactions,services,alerts,overview}")
    print("  POST /api/config  POST /api/control")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("bye")
        with _lock:
            global _decoy
            if _decoy is not None:
                _decoy.stop()
                _decoy = None


if __name__ == "__main__":
    main()
