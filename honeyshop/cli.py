"""Command-line interface for Honeyshop."""

import argparse
import logging
import sys

from rich.console import Console
from rich.logging import RichHandler

from .core import create_default_engine


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="honeyshop",
        description="Modular defensive honeypot framework",
    )
    parser.add_argument(
        "--ssh-port", type=int, default=2222, help="SSH honeypot port (default 2222)"
    )
    parser.add_argument(
        "--http-port", type=int, default=8080, help="HTTP honeypot port (default 8080)"
    )
    parser.add_argument(
        "--ftp-port", type=int, default=2121, help="FTP honeypot port (default 2121)"
    )
    parser.add_argument(
        "--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"]
    )

    args = parser.parse_args(argv)
    setup_logging(args.log_level)

    console = Console()
    console.print("[bold green]Honeyshop[/] – defensive honeypot framework")
    console.print(
        f"Starting services → SSH:{args.ssh_port}  HTTP:{args.http_port}  FTP:{args.ftp_port}"
    )
    console.print("[dim]Press Ctrl+C to stop[/]\n")

    engine = create_default_engine(
        ssh_port=args.ssh_port,
        http_port=args.http_port,
        ftp_port=args.ftp_port,
    )
    engine.run_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
