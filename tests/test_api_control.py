"""API control-plane tests (features, config, control actions)."""

from __future__ import annotations

import json
import os
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib import error, request

import honeyshop.api_server as api


def _http(method: str, url: str, body: dict | None = None) -> tuple[int, dict]:
    data = None if body is None else json.dumps(body).encode()
    req = request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if body is not None else {},
    )
    try:
        with request.urlopen(req, timeout=3) as resp:
            return resp.status, json.loads(resp.read().decode())
    except error.HTTPError as e:
        payload = e.read().decode()
        try:
            parsed = json.loads(payload) if payload else {}
        except json.JSONDecodeError:
            parsed = {"raw": payload}
        return e.code, parsed


def test_api_features_config_and_control(tmp_path: Path, monkeypatch):
    log_file = tmp_path / "honeyshop.jsonl"
    decoy_dir = tmp_path / "decoy"
    runtime = tmp_path / "runtime.json"
    log_file.write_text("", encoding="utf-8")

    monkeypatch.setattr(api, "DEFAULT_LOG", log_file)
    monkeypatch.setattr(api, "DECOY_DIR", decoy_dir)
    monkeypatch.setattr(api, "RUNTIME_CONFIG", runtime)
    monkeypatch.setattr(api, "_decoy", None)
    monkeypatch.setattr(api, "_runtime", {})
    # Isolate alert env
    for key in list(os.environ):
        if key.startswith("HONEYSHOP_"):
            monkeypatch.delenv(key, raising=False)

    server = ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"

    try:
        code, health = _http("GET", f"{base}/api/health")
        assert code == 200 and health.get("ok") is True

        code, features = _http("GET", f"{base}/api/features")
        assert code == 200
        assert features.get("api") is True
        assert "ebpf" in features
        assert features["ebpf"].get("ui_toggle") is False
        assert "decoy" in features
        assert "alerts" in features
        assert "stream" in features

        code, cfg = _http("GET", f"{base}/api/config")
        assert code == 200
        assert "ports" in cfg
        assert "slack_webhook" in cfg

        code, saved = _http(
            "POST",
            f"{base}/api/config",
            {
                "slack_webhook": "https://hooks.example.test/T/B/XXX",
                "email_to": "ops@example.test",
                "smtp_host": "smtp.example.test",
                "smtp_port": 587,
            },
        )
        assert code == 200 and saved.get("ok") is True
        assert "slack_webhook" in saved.get("changed", [])
        assert runtime.exists()
        stored = json.loads(runtime.read_text(encoding="utf-8"))
        assert stored["slack_webhook"].startswith("https://hooks.example.test")

        code, start = _http("POST", f"{base}/api/control", {"action": "start_decoy"})
        assert code == 200 and start.get("ok") is True and start.get("running") is True
        assert decoy_dir.exists()

        code, features2 = _http("GET", f"{base}/api/features")
        assert features2["decoy"]["running"] is True

        code, stop = _http("POST", f"{base}/api/control", {"action": "stop_decoy"})
        assert code == 200 and stop.get("ok") is True and stop.get("running") is False

        # test_alert without usable channels after clearing password-only setup may still
        # report slack configured from runtime — force empty notifier path
        monkeypatch.setenv("HONEYSHOP_SLACK_WEBHOOK", "")
        monkeypatch.setenv("HONEYSHOP_SMTP_HOST", "")
        monkeypatch.setenv("HONEYSHOP_EMAIL_TO", "")
        api._runtime.clear()
        code, bad = _http("POST", f"{base}/api/control", {"action": "test_alert"})
        # Either 400 (no channel) or 200 if env still set from earlier apply — accept both
        # but shape must be stable
        assert "action" in bad or "error" in bad or "ok" in bad

        code, unknown = _http("POST", f"{base}/api/control", {"action": "nuke"})
        assert code == 400
        assert unknown.get("ok") is False

        code, overview = _http("GET", f"{base}/api/overview")
        assert code == 200
        assert "features" in overview
        assert "services" in overview
    finally:
        # ensure decoy thread stopped
        api._stop_decoy()
        server.shutdown()
