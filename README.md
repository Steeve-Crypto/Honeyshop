# Honeyshop

Modular defensive honeypot framework.

## Features

- Low-interaction service modules (SSH, HTTP, FTP)
- Pluggable architecture
- Structured JSONL logging to file
- Easy multi-service orchestration
- Docker & docker-compose support

## Quick Start (local)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m honeyshop
```

Logs are written to `logs/honeyshop.jsonl` by default.

### Useful flags

```bash
python -m honeyshop --ssh-port 2222 --http-port 8080 --ftp-port 2121
python -m honeyshop --log-file /var/log/honeyshop.jsonl
python -m honeyshop --no-log-file          # console only
python -m honeyshop --log-level DEBUG
```

## Docker

```bash
docker compose up -d --build
```

View logs:
```bash
docker compose logs -f
# or
tail -f logs/honeyshop.jsonl
```

Stop:
```bash
docker compose down
```

## Architecture

```
honeyshop/
├── core.py              # Engine and orchestration
├── cli.py               # Command line interface
├── logging_setup.py     # JSONL + console logging
└── services/
    ├── base.py          # Abstract base service
    ├── ssh.py
    ├── http.py
    └── ftp.py
```

## Safety

This is a **defensive** tool only.  
Use only on systems you own or have explicit authorization to monitor.  
Do not expose honeypots to the public internet without proper isolation and legal review.

## License

MIT
