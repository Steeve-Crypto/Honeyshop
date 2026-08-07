# Honeyshop Web UI

Astro multi-page dashboard (obsidian + gold).

## Pages

| Route | Purpose |
|-------|---------|
| `/` | Overview + feature badges |
| `/live` | WS feed + poll fallback |
| `/services` | SSH / HTTP / FTP status |
| `/alerts` | Detections |
| `/settings` | Control plane (decoy, alerts, eBPF status) |

## Run

```bash
# terminal 1
python -m honeyshop.api_server
# terminal 2
python -m honeyshop.stream
# terminal 3
cd web
npm install
npm run dev
```

Open http://localhost:4321

Optional: `PUBLIC_HONEYSHOP_API=http://127.0.0.1:8787`  
Demo data is used when the API is offline.
