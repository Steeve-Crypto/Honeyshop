# Elastic Security Integration for Honeyshop

This folder helps you load Honeyshop Sigma rules into **Elastic Security** (Detection Engine) and run them as detection rules.

## Prerequisites

- Elastic Stack 8.x with **Elastic Security** enabled
- Security features turned on (our default `docker-compose.elk.yml` disables X-Pack security for simplicity — see notes below)
- Index pattern / data view: `honeyshop-*`
- Data already flowing from Honeyshop → Logstash/Filebeat → Elasticsearch

## 1. Enable Security (if using the sample compose)

The default Honeyshop ELK compose sets:

```yaml
xpack.security.enabled=false
```

For Elastic Security + Fleet you should enable security (or use Elastic Cloud).  
A production-oriented approach:

- Use [Elastic Cloud](https://cloud.elastic.co) (easiest)
- Or enable security on a self-managed cluster and create users/roles
- Or use the free basic license with security enabled

## 2. Import Detection Rules

### Option A – Manual (fastest)

1. Open Kibana → **Security → Rules → Detection rules (SIEM)**
2. **Create new rule** → **Custom query**
3. Use the queries from `detection-rules.json` or from `elk/alerts/README.md`
4. Set index pattern to `honeyshop-*`
5. Configure severity, risk score, schedule, and actions

### Option B – Convert Sigma → Elastic rule format

```bash
# Using sigma-cli / pySigma (install separately)
pip install pysigma pysigma-backend-elasticsearch

sigma convert -t elasticsearch -p ecs_windows \
  elk/sigma/honeyshop_suspicious_payload.yml
```

Then paste the resulting query into a Custom query rule in Elastic Security.

### Option C – Bulk import (NDJSON)

If you export rules from another Elastic Security instance, you can import them via:

**Security → Rules → Import rules**

A starter set of rule definitions is in `detection-rules.json` (use as reference when creating rules in the UI).

## 3. Recommended Detection Rules

| Rule name                         | Type      | Key condition                                      | Severity |
|-----------------------------------|-----------|----------------------------------------------------|----------|
| Honeyshop High Volume Source IP   | Threshold | same `source.ip` ≥ 20 in 5m                        | Medium   |
| Honeyshop Login Attempts          | Query     | `login_attempt` or SSH activity                    | Medium   |
| Honeyshop Suspicious Payload      | Query     | wget/curl/bash/Mirai/BusyBox patterns              | High     |
| Honeyshop Service Spike           | Threshold | any `honeypot.service` ≥ 50 in 5m                  | Low      |

Exact KQL and thresholds: see `elk/alerts/README.md` and `detection-rules.json`.

## 4. MITRE ATT&CK Mapping

The Sigma rules already carry tags:

- `attack.credential_access` / `T1110` (brute force)
- `attack.discovery` / `T1046` (network service discovery)
- `attack.execution` / `T1059` (command and scripting interpreter)

Map these in the Elastic rule **Threat** section when creating rules.

## 5. Actions

When a detection rule fires you can:

- Create a case in Elastic Security
- Send webhook (Slack, Discord, custom SOAR)
- Index into `honeyshop-alerts-*`
- Notify via email

## Notes

- Detection Engine is part of Elastic Security. Basic rules work on the free tier; advanced features may need a license.
- Always test rules with real honeypot traffic before enabling notifications.
- Tune thresholds after observing baseline noise from internet scanners.
