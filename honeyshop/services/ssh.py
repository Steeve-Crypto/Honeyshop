"""Low-interaction SSH honeypot."""

import socket
from .base import BaseService


class SSHService(BaseService):
    """Simple SSH banner + credential capture honeypot."""

    def __init__(self, host: str = "0.0.0.0", port: int = 2222):
        super().__init__(host=host, port=port, name="ssh")

    def handle_client(self, client: socket.socket, addr: tuple) -> None:
        # Send a realistic-looking SSH banner
        banner = b"SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.10\r\n"
        try:
            client.sendall(banner)
            self.log_interaction(addr, "banner_sent")

            # Read client identification / first data
            client.settimeout(10.0)
            data = client.recv(1024)
            if data:
                decoded = data.decode("utf-8", errors="replace").strip()
                self.log_interaction(addr, "client_data", decoded)

            # Keep connection briefly open to look more realistic
            client.settimeout(5.0)
            extra = client.recv(1024)
            if extra:
                self.log_interaction(
                    addr, "extra_data", extra.decode("utf-8", errors="replace")
                )
        except (socket.timeout, ConnectionResetError, BrokenPipeError):
            self.log_interaction(addr, "connection_closed")
        except Exception as e:
            self.log_interaction(addr, "error", str(e))
