#!/usr/bin/env python3
"""Start API + stream (+ optional engine) with one command.

  python scripts/honeyshop-up.py
  python scripts/honeyshop-up.py --engine
  python scripts/honeyshop-up.py --no-stream

Does not start the Astro UI (run: cd web && npm run dev).
Does not enable eBPF (needs root: python -m honeyshop --ebpf).
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Honeyshop process supervisor")
    parser.add_argument("--engine", action="store_true", help="also start python -m honeyshop")
    parser.add_argument("--no-stream", action="store_true", help="skip WebSocket stream")
    parser.add_argument("--no-api", action="store_true", help="skip API server")
    args = parser.parse_args()

    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(ROOT))
    if env["PYTHONPATH"] and str(ROOT) not in env["PYTHONPATH"].split(os.pathsep):
        env["PYTHONPATH"] = str(ROOT) + os.pathsep + env["PYTHONPATH"]

    procs: list[subprocess.Popen] = []
    cmds: list[list[str]] = []

    if not args.no_api:
        cmds.append([sys.executable, "-m", "honeyshop.api_server"])
    if not args.no_stream:
        cmds.append([sys.executable, "-m", "honeyshop.stream"])
    if args.engine:
        cmds.append([sys.executable, "-m", "honeyshop"])

    if not cmds:
        print("Nothing to start.")
        return 1

    print("Honeyshop supervisor")
    print(f"  root: {ROOT}")
    for cmd in cmds:
        print(f"  + {' '.join(cmd)}")
        procs.append(subprocess.Popen(cmd, cwd=str(ROOT), env=env))

    print("Ports: API :8787 · Stream :8788 · UI (manual) :4321")
    print("Ctrl+C to stop children.")

    def shutdown(*_):
        for p in procs:
            if p.poll() is None:
                p.terminate()
        deadline = time.time() + 5
        for p in procs:
            remaining = max(0.1, deadline - time.time())
            try:
                p.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                p.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    while True:
        alive = [p for p in procs if p.poll() is None]
        if not alive:
            codes = [p.returncode for p in procs]
            print(f"all children exited: {codes}")
            return max(c or 0 for c in codes)
        time.sleep(0.5)


if __name__ == "__main__":
    raise SystemExit(main())
