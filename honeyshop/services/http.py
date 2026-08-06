"""Low-interaction HTTP honeypot."""

import socket
from .base import BaseService


class HTTPService(BaseService):
    """Simple HTTP honeypot that logs requests and returns a fake page."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        super().__init__(host=host, port=port, name="http")

    def handle_client(self, client: socket.socket, addr: tuple) -> None:
        try:
            client.settimeout(8.0)
            request = b""
            while b"\r\n\r\n" not in request and len(request) < 8192:
                chunk = client.recv(1024)
                if not chunk:
                    break
                request += chunk

            if request:
                decoded = request.decode("utf-8", errors="replace")
                self.log_interaction(addr, "http_request", decoded)

            # Fake response
            body = b"<html><body><h1>It works!</h1></body></html>"
            response = (
                b"HTTP/1.1 200 OK\r\n"
                b"Server: Apache/2.4.41 (Ubuntu)\r\n"
                b"Content-Type: text/html\r\n"
                b"Content-Length: " + str(len(body)).encode() + b"\r\n"
                b"Connection: close\r\n"
                b"\r\n" + body
            )
            client.sendall(response)
            self.log_interaction(addr, "response_sent")
        except (socket.timeout, ConnectionResetError, BrokenPipeError):
            self.log_interaction(addr, "connection_closed")
        except Exception as e:
            self.log_interaction(addr, "error", str(e))
