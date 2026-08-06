# Honeyshop

Modular defensive honeypot framework.

## Features

- Low-interaction service modules (SSH, HTTP, FTP)
- Pluggable architecture
- Structured JSONL logging
- Docker & docker-compose support
- Optional **ELK Stack** integration + Kibana dashboard
- **Alerting rules** + Sigma rules

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

See `elk/dashboards/README.md` for manual setup if needed.

### Alerting Rules

Ready-to-use guidance and Sigma rules are in `elk/alerts/` and `elk/sigma/`.

**Recommended Kibana threshold / query rules:**

| Rule                        | Condition                          | Window |
|-----------------------------|------------------------------------|--------|
| High Volume Source IP       | same `source.ip` ≥ 20 events       | 5 min  |
| Login Attempts              | `login_attempt` or SSH activity ≥ 5| 10 min |
| Suspicious Payload          | wget/curl/bash/Mirai/etc. patterns | 5 min  |
| Service Spike               | any service ≥ 50 events            | 5 min  |

Full instructions, KQL queries, and Sigma YAML files:

- `elk/alerts/README.md`
- `elk/alerts/kibana-rules-examples.json`
- `elk/sigma/*.yml`

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
├── dashboards/
│   ├── honeyshop-dashboard.ndjson
│   └── README.md
├── alerts/
│   ├── README.md
│   └── kibana-rules-examples.json
└── sigma/
    ├── honeyshop_ssh_bruteforce.yml
    ├── honeyshop_login_attempt.yml
    ├── honeyshop_high_volume_ip.yml
    └── honeyshop_suspicious_payload.yml
```

## Safety

This is a **defensive** tool only.  
Use only on systems you own or have explicit authorization to monitor.  
Do not expose honeypots to the public internet without proper isolation and legal review.

## License

MIT
