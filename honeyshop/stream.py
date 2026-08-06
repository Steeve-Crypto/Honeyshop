"""WebSocket stream of honeyshop JSONL events.

  python -m honeyshop.stream
  → ws://127.0.0.1:8788/ws/interactions
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

import websockets
from websockets.asyncio.server import ServerConnection, serve

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = Path(os.environ.get("HONEYSHOP_LOG_FILE", str(ROOT / "logs" / "honeyshop.jsonl")))
HOST = os.environ.get("HONEYSHOP_WS_HOST", "127.0.0.1")
PORT = int(os.environ.get("HONEYSHOP_WS_PORT", "8788"))


def _normalize(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp": row.get("timestamp") or "",
        "service": row.get("service") or "unknown",
        "src_ip": row.get("src_ip") or "",
        "src_port": row.get("src_port") or 0,
        "event": row.get("event") or row.get("message") or "",
        "data": row.get("data") or "",
        "decoy": bool(row.get("decoy")),
    }


def _read_tail(path: Path, limit: int = 50) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
    except OSError:
        return []
    out: list[dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(_normalize(json.loads(line)))
        except json.JSONDecodeError:
            continue
    return out


async def _tail_file(path: Path, queue: asyncio.Queue) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch()
    pos = path.stat().st_size if path.exists() else 0
    while True:
        try:
            size = path.stat().st_size
            if size < pos:
                pos = 0
            if size > pos:
                with path.open("r", encoding="utf-8", errors="replace") as f:
                    f.seek(pos)
                    chunk = f.read()
                    pos = f.tell()
                for line in chunk.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        await queue.put(_normalize(json.loads(line)))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass
        await asyncio.sleep(0.35)


async def handler(ws: ServerConnection) -> None:
    path = ws.request.path if ws.request else "/"
    if path not in ("/ws/interactions", "/interactions", "/"):
        await ws.close(1008, "unknown path")
        return
    snapshot = _read_tail(DEFAULT_LOG, limit=80)
    await ws.send(json.dumps({"type": "snapshot", "items": list(reversed(snapshot))}))
    queue: asyncio.Queue = asyncio.Queue()
    tail_task = asyncio.create_task(_tail_file(DEFAULT_LOG, queue))
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=20.0)
                await ws.send(json.dumps({"type": "event", "item": event}))
            except asyncio.TimeoutError:
                await ws.send(json.dumps({"type": "ping"}))
    except websockets.ConnectionClosed:
        pass
    finally:
        tail_task.cancel()
        try:
            await tail_task
        except asyncio.CancelledError:
            pass


async def main() -> None:
    print(f"Honeyshop WS ws://{HOST}:{PORT}/ws/interactions")
    print(f"  log: {DEFAULT_LOG}")
    async with serve(handler, HOST, PORT):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
