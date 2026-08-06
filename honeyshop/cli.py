"""Command-line interface for Honeyshop."""

import argparse
import sys

from rich.console import Console

from .alerts import AlertConfig, Notifier
from .core import create_default_engine
from .decoy import DecoyLogGenerator
from .logging_setup import setup_logging
from .monitor import EbpfWatcher, default_event_handler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="honeyshop",
        description="Modular defensive honeypot framework",
    )
    parser.add_argument("--ssh-port", type=int, default=2222)
    parser.add_argument("--http-port", type=int, default=8080)
    parser.add_argument("--ftp-port", type=int, default=2121)
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--log-file", default="logs/honeyshop.jsonl")
    parser.add_argument("--no-log-file", action="store_true")
    parser.add_argument("--ebpf", action="store_true", help="eBPF process/file watch")
    parser.add_argument("--slack-webhook", default=None)
    parser.add_argument("--smtp-host", default=None)
    parser.add_argument("--smtp-port", type=int, default=587)
    parser.add_argument("--smtp-user", default=None)
    parser.add_argument("--smtp-password", default=None)
    parser.add_argument("--email-from", default=None)
    parser.add_argument("--email-to", default=None)
    parser.add_argument("--decoy", action="store_true")
    parser.add_argument("--decoy-dir", default="logs/decoy")

    args = parser.parse_args(argv)
    log_file = None if args.no_log_file else args.log_file
    setup_logging(level=args.log_level, log_file=log_file)

    console = Console()
    console.print("[bold green]Honeyshop[/] – defensive honeypot framework")
    console.print(f"Starting services → SSH:{args.ssh_port}  HTTP:{args.http_port}  FTP:{args.ftp_port}")

    alert_cfg = AlertConfig.from_env()
    if args.slack_webhook:
        alert_cfg.slack_webhook = args.slack_webhook
    if args.smtp_host:
        alert_cfg.smtp_host = args.smtp_host
    alert_cfg.smtp_port = args.smtp_port
    if args.smtp_user:
        alert_cfg.smtp_user = args.smtp_user
    if args.smtp_password:
        alert_cfg.smtp_password = args.smtp_password
    if args.email_from:
        alert_cfg.email_from = args.email_from
    if args.email_to:
        alert_cfg.email_to = args.email_to

    notifier = Notifier(alert_cfg)
    if notifier.enabled:
        console.print("[dim]Direct alerts enabled[/]")

    ebpf = None
    if args.ebpf:
        ok, reason = EbpfWatcher.available()
        if ok:
            ebpf = EbpfWatcher(on_event=default_event_handler(notifier))
            ebpf.start()
            console.print("[dim]eBPF watch on[/]")
        else:
            console.print(f"[yellow]eBPF skipped:[/] {reason}")

    decoy = None
    if args.decoy:
        decoy = DecoyLogGenerator(output_dir=args.decoy_dir, also_jsonl=log_file)
        decoy.start()
        console.print(f"[dim]Decoy logs → {args.decoy_dir}[/]")

    console.print("[dim]Press Ctrl+C to stop[/]\n")
    engine = create_default_engine(
        ssh_port=args.ssh_port, http_port=args.http_port, ftp_port=args.ftp_port
    )
    original_stop = engine.stop_all

    def stop_all():
        if ebpf:
            ebpf.stop()
        if decoy:
            decoy.stop()
        original_stop()

    engine.stop_all = stop_all  # type: ignore
    engine.run_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
