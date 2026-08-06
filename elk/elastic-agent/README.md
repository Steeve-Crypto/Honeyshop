# Elastic Agent Deployment for Honeyshop

Elastic Agent (managed by Fleet) is the modern way to collect logs, metrics, and security data into the Elastic Stack. This guide shows how to use it with Honeyshop.

## Architecture Options

```
┌─────────────────┐     JSONL      ┌──────────────────┐
│   Honeyshop     │ ────────────►  │  Elastic Agent   │
│  (honeypot)     │   (filestream) │  (Custom Logs)   │
└─────────────────┘                └────────┬─────────┘
                                            │
                                            ▼
                                   ┌──────────────────┐
                                   │  Elasticsearch   │
                                   │  + Elastic Sec.  │
                                   └──────────────────┘
```

You can:

1. **Keep Logstash** (current setup) and add Agent later for host metrics / other logs  
2. **Replace Logstash** with Elastic Agent + Custom Logs / Filestream integration  
3. **Run Agent on the same host** as Honeyshop to ship `logs/honeyshop.jsonl`

## Option 1 – Elastic Agent + Custom Logs (recommended for Agent path)

### 1. Enable Fleet in Kibana

1. Start a security-enabled Elastic Stack (Elastic Cloud is easiest)
2. Kibana → **Management → Fleet**
3. Add Fleet Server (Cloud does this for you; self-managed needs a Fleet Server)

### 2. Create an Agent Policy

- Name: `honeyshop-policy`
- Add integration: **Custom Logs** (or **Filestream**)

### 3. Custom Logs / Filestream settings

| Setting            | Value                                      |
|--------------------|--------------------------------------------|
| Log file path(s)   | `/var/log/honeyshop/honeyshop.jsonl`       |
| Data set           | `honeyshop.interactions`                   |
| Namespace          | `default`                                  |
| Processors         | Decode JSON fields if not already decoded  |

Map fields to match what the dashboard and rules expect:

- `src_ip` → `source.ip`
- `src_port` → `source.port`
- `service` → `honeypot.service`
- `event` → `honeypot.event`
- `data` → `honeypot.payload`

### 4. Install Elastic Agent on the Honeyshop host

**Linux:**
```bash
curl -L -O https://artifacts.elastic.co/downloads/beats/elastic-agent/elastic-agent-8.15.0-linux-x86_64.tar.gz
tar xzvf elastic-agent-8.15.0-linux-x86_64.tar.gz
cd elastic-agent-8.15.0-linux-x86_64
sudo ./elastic-agent install --url=<FLEET_URL> --enrollment-token=<TOKEN>
```

Use the enrollment token from the Agent Policy you created.

### 5. Docker-based Agent (side-by-side with Honeyshop)

See `docker-compose.agent.yml` for a sample that runs Elastic Agent alongside Honeyshop and mounts the log volume.

---

## Option 2 – Keep current Logstash pipeline

You do **not** need Elastic Agent for Honeyshop logs if Logstash is already shipping to Elasticsearch.  
Agent becomes useful when you want:

- Host metrics (CPU, disk, network)
- Endpoint security (Elastic Defend)
- Additional log sources on the same machine
- Centralized policy management via Fleet

---

## Option 3 – Elastic Cloud + Agent (simplest production path)

1. Create an Elastic Cloud deployment
2. Enable Fleet
3. Create policy + Custom Logs integration pointing at the honeypot log file
4. Install Agent on the VPS/host running Honeyshop
5. Import dashboard + create detection rules as documented

---

## Checklist

- [ ] Elastic Stack with security (or Elastic Cloud)
- [ ] Fleet Server available
- [ ] Agent policy with Custom Logs / Filestream
- [ ] Agent enrolled and healthy
- [ ] Logs appearing under data stream / index for honeyshop
- [ ] Data view created
- [ ] Dashboard imported / detection rules created

## Notes

- Elastic Agent version should match (or be compatible with) your Elasticsearch version.
- Our sample `docker-compose.elk.yml` is intentionally simple and **does not** run Fleet Server. Use Elastic Cloud or a full self-managed Fleet setup for production Agent management.
- For a pure honeypot log pipeline, Logstash remains perfectly valid; Agent is the better long-term choice when you grow into host monitoring and Elastic Security.
