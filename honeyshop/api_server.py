"""Minimal HTTP API for the Honeyshop UI. python -m honeyshop.api_server"""

from __future__ import annotations

import json
import os
import socket
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = Path(os.environ.get("HONEYSHOP_LOG_FILE", str(ROOT / "logs" / "honeyshop.jsonl")))
DECOY_DIR = Path(os.environ.get("HONEYSHOP_DECOY_DIR", str(ROOT / "logs" / "decoy")))
HOST = os.environ.get("HONEYSHOP_API_HOST", "127.0.0.1")
PORT = int(os.environ.get("HONEYSHOP_API_PORT", "8787"))
DEFAULT_PORTS = {"ssh": 2222, "http": 8080, "ftp": 2121}


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
            alerts.append({"id": f"payload-{len(alerts)}", "severity": "high", "title": "Suspicious payload", "detail": data[:160], "time": row.get("timestamp") or ""})
        if "login" in event:
            alerts.append({"id": f"login-{len(alerts)}", "severity": "medium", "title": "Login attempt", "detail": f"{row.get('service','?')} from {ip}", "time": row.get("timestamp") or ""})
        if row.get("service") == "ebpf" or event in ("exec", "open"):
            alerts.append({"id": f"ebpf-{len(alerts)}", "severity": "medium", "title": f"eBPF {event}", "detail": data[:160], "time": row.get("timestamp") or ""})
    for ip, n in ip_counts.items():
        if n >= 8:
            alerts.append({"id": f"vol-{ip}", "severity": "medium", "title": "High volume source IP", "detail": f"{ip} → {n} events", "time": datetime.now(timezone.utc).isoformat()})
    seen, uniq = set(), []
    for a in alerts:
        key = (a["title"], a["detail"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(a)
    return uniq[:40]


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
        "decoy_active": bool(decoy_files),
        "decoy_files": [p.name for p in decoy_files],
        "alerts_configured": bool(os.environ.get("HONEYSHOP_SLACK_WEBHOOK") or os.environ.get("HONEYSHOP_EMAIL_TO")),
    }


def _norm(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp": row.get("timestamp") or "",
        "service": row.get("service") or "unknown",
        "src_ip": row.get("src_ip") or "",
        "src_port": row.get("src_port") or 0,
        "event": row.get("event") or row.get("message") or "",
        "data": row.get("data") or "",
        "decoy": bool(row.get("decoy")),
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")

    def _json(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

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
            ips = {}
            for r in rows:
                ip = r.get("src_ip") or ""
                if ip:
                    ips[ip] = ips.get(ip, 0) + 1
            return self._json(200, {
                "services": services,
                "alerts": _alerts_from_logs(rows)[:8],
                "recent": [_norm(r) for r in rows[:12]],
                "total_hits": sum(s["hits"] for s in services),
                "unique_sources": len(ips),
                "status": _status(),
            })
        self._json(404, {"error": "not found"})


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Honeyshop API http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("bye")


if __name__ == "__main__":
    main()
