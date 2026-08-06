"""Basic tests for Honeyshop services."""

import time
from honeyshop.services.ssh import SSHService
from honeyshop.services.http import HTTPService


def test_ssh_starts_and_stops():
    svc = SSHService(port=0)  # ephemeral port
    svc.start()
    assert svc.port > 0
    time.sleep(0.2)
    svc.stop()


def test_http_starts_and_stops():
    svc = HTTPService(port=0)
    svc.start()
    assert svc.port > 0
    time.sleep(0.2)
    svc.stop()
