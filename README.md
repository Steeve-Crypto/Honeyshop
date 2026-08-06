# Honeyshop

Modular defensive honeypot framework.

## Features

- Low-interaction service modules (SSH, HTTP, FTP)
- Pluggable architecture
- Structured JSONL logging
- Docker & docker-compose support
- Optional **ELK Stack** + Kibana dashboard
- **Alerting** + Sigma rules
- **Elastic Security** detection rule guidance
- **Elastic Agent** deployment options

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
python -m honeyshop --no-log-file
python -m honeyshop --log-level DEBUG
```

## Docker (honeypot only)

```bash
docker compose up -d --build
```

## ELK Stack Integration

```bash
docker compose -f docker-compose.yml -f docker-compose.elk.yml up -d --build
```

| Service        | URL / Port              |
|----------------|-------------------------|
| Honeypot SSH   | `:2222`                 |
| Honeypot HTTP  | `:8080`                 |
| Honeypot FTP   | `:2121`                 |
| Elasticsearch  | http://localhost:9200   |
| Kibana         | http://localhost:5601   |

### Dashboard

Import `elk/dashboards/honeyshop-dashboard.ndjson` via  
**Stack Management → Saved Objects → Import**.

### Alerting & Sigma

- Kibana threshold/query rules: `elk/alerts/`
- Sigma rules: `elk/sigma/`

### Elastic Security

Convert/import Sigma-style detections into the Detection Engine:

- Guide: `elk/elastic-security/README.md`
- Rule reference: `elk/elastic-security/detection-rules.json`

### Elastic Agent

Ship Honeyshop logs via Fleet-managed Elastic Agent (alternative or complement to Logstash):

- Guide: `elk/elastic-agent/README.md`
- Sample compose: `elk/elastic-agent/docker-compose.agent.yml`

## Architecture

```
honeyshop/
├── core.py, cli.py, logging_setup.py
└── services/ (ssh, http, ftp)

elk/
├── logstash.conf / filebeat.yml
├── dashboards/
├── alerts/
├── sigma/
├── elastic-security/     # Detection Engine integration
└── elastic-agent/        # Fleet / Agent deployment
```

## Safety

This is a **defensive** tool only.  
Use only on systems you own or have explicit authorization to monitor.  
Do not expose honeypots to the public internet without proper isolation and legal review.

## License

MIT
