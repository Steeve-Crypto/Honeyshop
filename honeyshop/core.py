"""Core orchestration for Honeyshop."""

from __future__ import annotations

import logging
import signal
import sys
from typing import List

from .services.base import BaseService
from .services.ssh import SSHService
from .services.http import HTTPService
from .services.ftp import FTPService

logger = logging.getLogger("honeyshop")


class HoneyshopEngine:
    """Manages multiple honeypot services."""

    def __init__(self):
        self.services: List[BaseService] = []
        self._running = False

    def add_service(self, service: BaseService) -> None:
        self.services.append(service)

    def start_all(self) -> None:
        if not self.services:
            logger.warning("No services configured")
            return

        for svc in self.services:
            svc.start()
        self._running = True
        logger.info("Honeyshop engine started with %d services", len(self.services))

    def stop_all(self) -> None:
        for svc in self.services:
            svc.stop()
        self._running = False
        logger.info("Honeyshop engine stopped")

    def run_forever(self) -> None:
        """Start all services and block until interrupted."""
        self.start_all()

        def _shutdown(signum, frame):
            logger.info("Shutdown signal received")
            self.stop_all()
            sys.exit(0)

        signal.signal(signal.SIGINT, _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)

        # Keep main thread alive
        import time
        while self._running:
            time.sleep(1)


def create_default_engine(
    ssh_port: int = 2222,
    http_port: int = 8080,
    ftp_port: int = 2121,
) -> HoneyshopEngine:
    """Factory that creates an engine with the default low-interaction services."""
    engine = HoneyshopEngine()
    engine.add_service(SSHService(port=ssh_port))
    engine.add_service(HTTPService(port=http_port))
    engine.add_service(FTPService(port=ftp_port))
    return engine
