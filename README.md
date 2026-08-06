# Honeyshop

Modular defensive honeypot framework.

## Features

- Low-interaction service modules (SSH, HTTP, FTP)
- Pluggable architecture
- Structured JSONL logging
- Docker & docker-compose support
- Optional **ELK Stack** integration + ready Kibana dashboard

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

View logs:
```bash
docker compose logs -f
tail -f logs/honeyshop.jsonl
```

## ELK Stack Integration

Honeyshop can ship its JSONL logs into Elasticsearch via Logstash for analysis in Kibana.

### Start full stack (Honeyshop + ELK)

```bash
docker compose -f docker-compose.yml -f docker-compose.elk.yml up -d --build
```

### Access

| Service        | URL / Port              |
|----------------|-------------------------|
| Honeypot SSH   | `:2222`                 |
| Honeypot HTTP  | `:8080`                 |
| Honeypot FTP   | `:2121`                 |
| Elasticsearch  | http://localhost:9200   |
| Kibana         | http://localhost:5601   |

### Import the Honeyshop Dashboard

1. Open http://localhost:5601
2. Go to **Stack Management → Saved Objects**
3. Click **Import**
4. Select `elk/dashboards/honeyshop-dashboard.ndjson`
5. Open **Dashboard → Honeyshop Overview**

The dashboard includes:
- Interactions over time
- Breakdown by service (SSH / HTTP / FTP)
- Event type distribution
- Top source IPs
- Recent interactions table

See `elk/dashboards/README.md` for manual setup instructions if the import fails.

### Log fields available in Elasticsearch

| Field               | Description                  |
|---------------------|------------------------------|
| `@timestamp`        | Event time                   |
| `source.ip`         | Attacker IP                  |
| `source.port`       | Source port                  |
| `honeypot.service`  | Service hit (ssh/http/ftp)   |
| `honeypot.event`    | Event type                   |
| `honeypot.payload`  | Captured data / payload      |
| `geoip.*`           | GeoIP enrichment (if enabled)|

### Alternative: Filebeat instead of Logstash

A sample `elk/filebeat.yml` is included if you prefer Filebeat.

## Architecture

```
honeyshop/
├── core.py
├── cli.py
├── logging_setup.py
└── services/
    ├── base.py
    ├── ssh.py
    ├── http.py
    └── ftp.py

elk/
├── logstash.conf
├── filebeat.yml
└── dashboards/
    ├── honeyshop-dashboard.ndjson
    └── README.md
```

## Safety

This is a **defensive** tool only.  
Use only on systems you own or have explicit authorization to monitor.  
Do not expose honeypots to the public internet without proper isolation and legal review.

## License

MIT
