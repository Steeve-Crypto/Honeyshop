# Honeyshop Alerting

This directory contains Sigma rules and ready-to-use Kibana alerting guidance for Honeyshop.

## 1. Kibana Threshold Rules (recommended)

Open **Kibana → Stack Management → Rules** (or **Observability / Security → Alerts** depending on your license) and create the following rules.

### Rule 1 – High volume from single IP

| Setting              | Value                                      |
|----------------------|--------------------------------------------|
| Rule type            | Elasticsearch query / Threshold            |
| Index                | `honeyshop-*`                              |
| Group by             | `source.ip`                                |
| Condition            | Count `>= 20`                              |
| Time window          | Last 5 minutes                             |
| Check every          | 1 minute                                   |
| Action               | Email / Slack / Webhook / Index            |

**KQL filter (optional):**
```
honeypot.service: *
```

### Rule 2 – SSH / Login attempts

| Setting              | Value                                      |
|----------------------|--------------------------------------------|
| Rule type            | Elasticsearch query                        |
| Index                | `honeyshop-*`                              |
| Query                | `honeypot.event: "login_attempt" or honeypot.service: "ssh"` |
| Condition            | Count `>= 5` in last 10 minutes            |
| Action               | Notify                                     |

### Rule 3 – Suspicious payloads

| Setting              | Value                                      |
|----------------------|--------------------------------------------|
| Rule type            | Elasticsearch query                        |
| Index                | `honeyshop-*`                              |
| Query                | See KQL below                              |
| Condition            | Count `>= 1`                               |
| Action               | High priority notify                       |

**KQL:**
```
honeypot.payload: (*wget* or *curl* or *"/bin/bash"* or *"/bin/sh"* or *"nc -e"* or *"python -c"* or *base64* or *"chmod +x"* or *Mirai* or *BusyBox*)
```

### Rule 4 – Service Spike

| Setting              | Value                                      |
|----------------------|--------------------------------------------|
| Rule type            | Threshold                                  |
| Index                | `honeyshop-*`                              |
| Group by             | `honeypot.service`                         |
| Condition            | Count `>= 50` in 5 minutes                 |
| Action               | Notify                                     |

---

## 2. Sigma Rules

Sigma rules are located in `elk/sigma/`:

| File                              | Purpose                          |
|-----------------------------------|----------------------------------|
| `honeyshop_ssh_bruteforce.yml`    | SSH activity                     |
| `honeyshop_login_attempt.yml`     | Login / credential events        |
| `honeyshop_high_volume_ip.yml`    | High volume source (threshold in Kibana) |
| `honeyshop_suspicious_payload.yml`| Common malware/exploit strings   |

### Using Sigma rules

**Option A – Convert with sigconverter / sigmac**
```bash
# Example with pySigma / sigma-cli
sigma convert -t elasticsearch -p ecs_windows elk/sigma/*.yml
```

**Option B – Elastic Security**
If you enable Elastic Security, you can import Sigma rules via the Detection Engine or community tools that convert Sigma → Elastic rule format.

**Option C – Manual**
Use the KQL queries above; they are already derived from the Sigma detections.

---

## 3. Suggested Actions

When an alert fires you can:

- Write the alert to another Elasticsearch index (`honeyshop-alerts-*`)
- Send a webhook (Discord, Slack, custom)
- Email the security team
- Create a case in Elastic Security (if licensed)

---

## 4. Quick Start Checklist

1. Start ELK + Honeyshop
2. Confirm data is arriving in `honeyshop-*`
3. Create the 3–4 threshold / query rules above in Kibana
4. (Optional) Import or convert the Sigma rules
5. Test by connecting to the honeypot ports and verifying alerts fire

## Notes

- Our default `docker-compose.elk.yml` disables X-Pack security for simplicity. For production, enable security and configure proper authentication before exposing alerting webhooks.
- Threshold values (20 events / 5 min, etc.) are starting points — tune them to your environment.
