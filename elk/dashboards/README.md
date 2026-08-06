# Honeyshop Kibana Dashboard

## Quick Import (recommended)

1. Start the ELK stack:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.elk.yml up -d --build
   ```

2. Open Kibana → http://localhost:5601

3. Go to **Stack Management → Saved Objects**

4. Click **Import** and select:
   ```
   elk/dashboards/honeyshop-dashboard.ndjson
   ```

5. Check **Create new objects with random IDs** (or overwrite if re-importing)

6. After import, open **Dashboard → Honeyshop Overview**

## Manual Setup (if import fails)

### 1. Create Data View
- **Stack Management → Data Views → Create data view**
- Name: `honeyshop-*`
- Index pattern: `honeyshop-*`
- Timestamp field: `@timestamp`

### 2. Create Visualizations

| Visualization              | Type            | Aggregation / Field              |
|---------------------------|-----------------|----------------------------------|
| Interactions Over Time    | Line            | Count + Date Histogram on `@timestamp` |
| By Service                | Pie / Donut     | Terms on `honeypot.service`      |
| Event Types               | Pie             | Terms on `honeypot.event`        |
| Top Source IPs            | Horizontal Bar  | Terms on `source.ip` (size 15)   |
| Recent Interactions       | Saved Search    | Columns: service, ip, port, event, payload |

### 3. Build Dashboard
- Create a new Dashboard named **Honeyshop Overview**
- Add the visualizations above
- Suggested layout:
  - Top row: Timeline (wide) + By Service + Event Types
  - Bottom row: Top Source IPs + Recent Interactions table

## Useful KQL queries

```
honeypot.service: "ssh"
honeypot.event: "login_attempt"
source.ip: "1.2.3.4"
honeypot.payload: *admin*
```

## Notes
- Make sure Logstash has processed some events before the dashboard shows data.
- GeoIP fields appear only if the GeoIP database is available in Logstash.
