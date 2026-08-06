"""Low-interaction FTP honeypot."""

import socket
from .base import BaseService


class FTPService(BaseService):
    """Simple FTP banner + login capture honeypot."""

    def __init__(self, host: str = "0.0.0.0", port: int = 2121):
        super().__init__(host=host, port=port, name="ftp")

    def handle_client(self, client: socket.socket, addr: tuple) -> None:
        try:
            client.settimeout(15.0)
            # Send welcome banner
            client.sendall(b"220 Welcome to FTP server\r\n")
            self.log_interaction(addr, "banner_sent")

            while True:
                data = client.recv(1024)
                if not data:
                    break
                cmd = data.decode("utf-8", errors="replace").strip()
                self.log_interaction(addr, "ftp_command", cmd)

                upper = cmd.upper()
                if upper.startswith("USER"):
                    client.sendall(b"331 Please specify the password.\r\n")
                elif upper.startswith("PASS"):
                    client.sendall(b"530 Login incorrect.\r\n")
                    self.log_interaction(addr, "login_attempt", cmd)
                elif upper.startswith("QUIT"):
                    client.sendall(b"221 Goodbye.\r\n")
                    break
                else:
                    client.sendall(b"500 Unknown command.\r\n")
        except (socket.timeout, ConnectionResetError, BrokenPipeError):
            self.log_interaction(addr, "connection_closed")
        except Exception as e:
            self.log_interaction(addr, "error", str(e))
