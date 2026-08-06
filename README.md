<p align="center">
  <img src="docs/assets/logo.svg" alt="Honeyshop logo" width="120" height="120"/>
</p>

<h1 align="center">Honeyshop</h1>

<p align="center">
  <strong>Modular defensive honeypot framework</strong><br/>
  Detect · Deceive · Defend
</p>

<p align="center">
  <img src="docs/assets/banner.svg" alt="Honeyshop banner" width="100%"/>
</p>

<p align="center">
  <a href="#quick-start-local">Quick Start</a> ·
  <a href="#docker-honeypot-only">Docker</a> ·
  <a href="#elk-stack-integration">ELK</a> ·
  <a href="#safety">Safety</a>
</p>

---

## Features

- Low-interaction service modules (SSH, HTTP, FTP)
- Pluggable architecture
- Structured JSONL logging
- Docker & docker-compose support
- Optional **ELK Stack** + Kibana dashboard
- **Alerting** + Sigma rules
- **Elastic Security** detection rule guidance
- **Elastic Agent** deployment options

## Brand

| Asset | Path | Use |
|-------|------|-----|
| Logo | [`docs/assets/logo.svg`](docs/assets/logo.svg) | Icon, favicon, README |
| Banner | [`docs/assets/banner.svg`](docs/assets/banner.svg) | Hero / social header |
| Social (raster) | `docs/assets/social.jpg` | OG image, posts |
| Banner (raster) | `docs/assets/banner.jpg` | Marketing slides |
| Logo (raster) | `docs/assets/logo.jpg` | App stores, avatars |

**Colors:** Navy `#0B1220` · Amber `#F5C16C` → `#D4922A` · Cream `#F5E6C8`

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

- Guide: `elk/elastic-security/README.md`
- Rule reference: `elk/elastic-security/detection-rules.json`

### Elastic Agent

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
├── elastic-security/
└── elastic-agent/

docs/assets/          # Logo, banner, social images
```

## Safety

This is a **defensive** tool only.  
Use only on systems you own or have explicit authorization to monitor.  
Do not expose honeypots to the public internet without proper isolation and legal review.

## License

MIT
