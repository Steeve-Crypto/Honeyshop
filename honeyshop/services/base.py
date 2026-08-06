"""Base class for all honeypot services."""

from abc import ABC, abstractmethod
from typing import Optional
import socket
import threading
import logging
from datetime import datetime, timezone

logger = logging.getLogger("honeyshop.services")


class BaseService(ABC):
    """Abstract base for low-interaction honeypot services."""

    def __init__(self, host: str = "0.0.0.0", port: int = 0, name: str = "base"):
        self.host = host
        self.port = port
        self.name = name
        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    @abstractmethod
    def handle_client(self, client: socket.socket, addr: tuple) -> None:
        """Handle a single client connection. Must be implemented by subclasses."""
        pass

    def start(self) -> None:
        """Start the service listener in a background thread."""
        if self._running:
            return

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.listen(50)
        self._sock.settimeout(1.0)

        # Update port if it was 0 (ephemeral)
        self.port = self._sock.getsockname()[1]

        self._running = True
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()
        logger.info("%s listening on %s:%s", self.name, self.host, self.port)

    def stop(self) -> None:
        """Stop the service."""
        self._running = False
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("%s stopped", self.name)

    def _accept_loop(self) -> None:
        while self._running:
            try:
                client, addr = self._sock.accept()
                t = threading.Thread(
                    target=self._safe_handle, args=(client, addr), daemon=True
                )
                t.start()
            except socket.timeout:
                continue
            except OSError:
                if self._running:
                    logger.exception("Accept error on %s", self.name)
                break

    def _safe_handle(self, client: socket.socket, addr: tuple) -> None:
        try:
            self.handle_client(client, addr)
        except Exception:
            logger.exception("Error handling client %s on %s", addr, self.name)
        finally:
            try:
                client.close()
            except OSError:
                pass

    def log_interaction(self, addr: tuple, event: str, data: str = "") -> None:
        """Structured log helper that works with JSON formatter."""
        logger.info(
            "interaction",
            extra={
                "service": self.name,
                "src_ip": addr[0],
                "src_port": addr[1],
                "event": event,
                "data": data[:2048],
            },
        )
