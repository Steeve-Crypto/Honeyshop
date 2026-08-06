"""Command-line interface for Honeyshop."""

import argparse
import sys

from rich.console import Console

from .core import create_default_engine
from .logging_setup import setup_logging


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
    parser.add_argument(
        "--log-file",
        default="logs/honeyshop.jsonl",
        help="JSONL log file path (default: logs/honeyshop.jsonl)",
    )
    parser.add_argument(
        "--no-log-file",
        action="store_true",
        help="Disable file logging",
    )

    args = parser.parse_args(argv)

    log_file = None if args.no_log_file else args.log_file
    setup_logging(level=args.log_level, log_file=log_file)

    console = Console()
    console.print("[bold green]Honeyshop[/] – defensive honeypot framework")
    console.print(
        f"Starting services → SSH:{args.ssh_port}  HTTP:{args.http_port}  FTP:{args.ftp_port}"
    )
    if log_file:
        console.print(f"[dim]Logging interactions to {log_file}[/]")
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
