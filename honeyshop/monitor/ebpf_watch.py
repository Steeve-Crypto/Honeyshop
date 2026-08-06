"""eBPF process + file watch via bpftrace. Linux only."""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger("honeyshop.monitor")
SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"
IGNORE_COMMS = {"bpftrace", "systemd", "kworker", "honeyshop"}
HIGH_PATTERNS = re.compile(
    r"(curl|wget|nc\.|ncat|python|perl|ruby|bash|/bin/sh|chmod|id_rsa|\.ssh|shadow|passwd|sudoers|base64|/dev/tcp|socat|linpeas)",
    re.I,
)


class EbpfWatcher:
    def __init__(self, on_event: Callable[[dict], None], watch_exec: bool = True, watch_open: bool = True):
        self.on_event = on_event
        self.watch_exec = watch_exec
        self.watch_open = watch_open
        self._procs: list[subprocess.Popen] = []
        self._running = False

    @staticmethod
    def available() -> tuple[bool, str]:
        if shutil.which("bpftrace") is None:
            return False, "bpftrace not found (install bpftrace; Linux root required)"
        if os.geteuid() != 0:
            return False, "eBPF watch needs root (or CAP_BPF)"
        return True, "ok"

    def start(self) -> None:
        ok, reason = self.available()
        if not ok:
            logger.warning("eBPF watcher disabled: %s", reason)
            return
        self._running = True
        if self.watch_exec:
            self._spawn(SCRIPTS_DIR / "execsnoop.bt")
        if self.watch_open:
            self._spawn(SCRIPTS_DIR / "opensnoop.bt")
        logger.info("eBPF watcher started")

    def stop(self) -> None:
        self._running = False
        for p in self._procs:
            try:
                p.terminate()
                p.wait(timeout=3)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
        self._procs.clear()

    def _spawn(self, script: Path) -> None:
        if not script.exists():
            logger.error("Missing script: %s", script)
            return
        try:
            proc = subprocess.Popen(
                ["bpftrace", str(script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except OSError as e:
            logger.error("bpftrace start failed: %s", e)
            return
        self._procs.append(proc)
        threading.Thread(target=self._read_loop, args=(proc,), daemon=True).start()

    def _read_loop(self, proc: subprocess.Popen) -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            if not self._running:
                break
            line = line.strip()
            if not line or line.startswith("Attaching"):
                continue
            event = self._parse(line)
            if event is None or event.get("comm") in IGNORE_COMMS:
                continue
            try:
                self.on_event(event)
            except Exception:
                logger.exception("on_event failed")

    def _parse(self, line: str) -> Optional[dict]:
        parts = line.split("|", 4)
        if len(parts) < 5 or parts[0] not in ("exec", "open"):
            return None
        kind, pid, uid, comm, target = parts
        try:
            return {
                "type": kind,
                "pid": int(pid),
                "uid": int(uid),
                "comm": comm,
                "target": target,
                "severity": "high" if HIGH_PATTERNS.search(f"{comm} {target}") else "medium",
            }
        except ValueError:
            return None


def default_event_handler(notifier) -> Callable[[dict], None]:
    def handle(event: dict) -> None:
        title = f"eBPF {event['type']}: {event['comm']}"
        body = f"pid={event['pid']} uid={event['uid']}\ncomm={event['comm']}\ntarget={event['target']}\n"
        logger.info(
            "ebpf_event",
            extra={
                "service": "ebpf",
                "src_ip": "local",
                "src_port": 0,
                "event": event["type"],
                "data": f"{event['comm']} -> {event['target']}",
            },
        )
        if notifier and notifier.enabled:
            notifier.send(title, body, severity=event.get("severity", "medium"))

    return handle
