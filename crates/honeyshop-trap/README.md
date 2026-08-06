# honeyshop-trap

Rust multi-port trap listeners for Honeyshop.

- **std only** (no crates.io deps) — builds on older rustc
- Same **JSONL** schema as Python (`trap: "rust"`)
- Works with existing API `:8787` and WebSocket `:8788`

## Build

```bash
cd crates/honeyshop-trap
cargo build --release
```

## Run (repo root)

```bash
./crates/honeyshop-trap/target/release/honeyshop-trap \
  crates/honeyshop-trap/config.example.toml
```

Do not bind the same ports as Python listeners at the same time.

## Hybrid

```
Internet → honeyshop-trap (Rust) → logs/honeyshop.jsonl
              python -m honeyshop.api_server
              python -m honeyshop.stream
              cd web && npm run dev
```
