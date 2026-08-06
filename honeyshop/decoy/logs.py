"""Generate fake but realistic logs to waste attacker time."""

from __future__ import annotations

import logging
import os
import random
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("honeyshop.decoy")

FAKE_USERS = ["admin", "ubuntu", "deploy", "backup", "jenkins", "root"]
FAKE_IPS = ["10.0.3.12", "10.0.3.44", "192.168.10.5", "172.16.2.8", "203.0.113.90"]
AUTH_TEMPLATES = [
    "{ts} {host} sshd[{pid}]: Accepted publickey for {user} from {ip} port {port} ssh2",
    "{ts} {host} sshd[{pid}]: Failed password for invalid user {user} from {ip} port {port} ssh2",
    "{ts} {host} sudo: {user} : TTY=pts/0 ; PWD=/home/{user} ; USER=root ; COMMAND=/usr/bin/systemctl",
]
APP_TEMPLATES = [
    "{ts} INFO  [http] 200 GET /api/v1/health from={ip}",
    "{ts} INFO  [worker] job completed id={pid}",
    "{ts} WARN  [auth] rate-limit soft trip ip={ip} user={user}",
]


class DecoyLogGenerator:
    def __init__(self, output_dir: str = "logs/decoy", interval_sec: float = 8.0, also_jsonl: Optional[str] = None):
        self.output_dir = Path(output_dir)
        self.interval = interval_sec
        self.also_jsonl = also_jsonl
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.host = os.uname().nodename if hasattr(os, "uname") else "honeyshop"

    def start(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Decoy log generator → %s", self.output_dir)

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _loop(self) -> None:
        auth_path = self.output_dir / "auth.log"
        app_path = self.output_dir / "app.log"
        while self._running:
            try:
                self._append(auth_path, self._auth_line())
                if random.random() < 0.6:
                    self._append(app_path, self._app_line())
                if self.also_jsonl and random.random() < 0.3:
                    self._jsonl_noise()
            except Exception:
                logger.exception("decoy write failed")
            time.sleep(self.interval + random.uniform(-2, 3))

    def _ts(self) -> str:
        return datetime.now(timezone.utc).strftime("%b %d %H:%M:%S")

    def _auth_line(self) -> str:
        tpl = random.choice(AUTH_TEMPLATES)
        return tpl.format(
            ts=self._ts(), host=self.host, pid=random.randint(1000, 32000),
            user=random.choice(FAKE_USERS), ip=random.choice(FAKE_IPS),
            port=random.randint(1024, 65000),
        )

    def _app_line(self) -> str:
        tpl = random.choice(APP_TEMPLATES)
        return tpl.format(
            ts=datetime.now(timezone.utc).isoformat(),
            ip=random.choice(FAKE_IPS), user=random.choice(FAKE_USERS),
            pid=random.randint(1, 9999),
        )

    def _append(self, path: Path, line: str) -> None:
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _jsonl_noise(self) -> None:
        import json
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "INFO",
            "logger": "honeyshop.services",
            "message": "interaction",
            "service": random.choice(["ssh", "http", "ftp"]),
            "src_ip": random.choice(FAKE_IPS),
            "src_port": random.randint(1024, 65000),
            "event": random.choice(["banner_sent", "http_request", "login_attempt"]),
            "data": "systemctl status nginx",
            "decoy": True,
        }
        path = Path(self.also_jsonl)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
