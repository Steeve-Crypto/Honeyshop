# Honeyshop

Modular defensive honeypot framework.

## Features

- Low-interaction service modules (SSH, HTTP, FTP)
- Pluggable architecture
- Structured JSON logging
- Easy multi-service orchestration
- Docker-ready

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m honeyshop
```

## Architecture

```
honeyshop/
├── core.py         # Engine and orchestration
├── services/       # Individual honeypot modules
├── cli.py          # Command line interface
└── __main__.py
```

## Safety

This is a **defensive** tool only.  
Use only on systems you own or have explicit authorization to monitor.  
Do not expose honeypots to the public internet without proper isolation and legal review.

## License

MIT
