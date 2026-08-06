# honeyshop-trap

Rust multi-port trap listeners for Honeyshop.

- **Current build:** `std` only (thread-per-connection), no crates.io deps
- Same **JSONL** as Python (`trap: "rust"`)
- Works with API `:8787` and WebSocket `:8788`

## Build

```bash
cd crates/honeyshop-trap && cargo build --release
```

## Run (repo root)

```bash
./crates/honeyshop-trap/target/release/honeyshop-trap \
  crates/honeyshop-trap/config.example.toml
```

Do not bind the same ports as Python listeners.

## Hybrid

```
Internet → honeyshop-trap (Rust) → logs/honeyshop.jsonl
              python -m honeyshop.api_server
              python -m honeyshop.stream
              cd web && npm run dev
```

---

## Tokio backport instructions

Shipped code uses **std + threads** so older rustc (e.g. 1.75) builds when crates.io resolves `edition2024`-only crates.

With **Rust 1.85+** (or current stable that resolves tokio cleanly), switch to **tokio** for cheaper concurrency under scan floods.

### 1. Prerequisites

```bash
rustup update stable
rustc --version   # prefer 1.85+
```

### 2. Cargo.toml

```toml
[package]
name = "honeyshop-trap"
version = "0.1.0"
edition = "2021"
publish = false

[dependencies]
tokio = { version = "1", features = [
  "rt-multi-thread", "macros", "net", "io-util",
  "sync", "time", "signal", "fs",
] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
toml = "0.8"
chrono = { version = "0.4", default-features = false, features = ["clock", "std"] }
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter"] }

[profile.release]
lto = true
codegen-units = 1
strip = true
```

### 3. Map std → tokio

| std today | tokio |
|-----------|--------|
| `TcpListener` + thread accept | `tokio::net::TcpListener` + `accept().await` |
| `thread::spawn` | `tokio::spawn` |
| `Mutex` log lock | `tokio::sync::Mutex` or `mpsc` writer task |
| `set_read_timeout` | `tokio::time::timeout` |
| blocking read/write | `AsyncReadExt` / `AsyncWriteExt` |
| join threads | `tokio::signal::ctrl_c().await` |

**Keep JSONL fields identical:** `timestamp`, `service`, `src_ip`, `src_port`, `event`, `data`, `trap: "rust"`.

### 4. Accept loop skeleton

```rust
async fn accept_loop(listener: TcpListener, svc: ServiceCfg, shared: Arc<Shared>) {
    loop {
        let (stream, peer) = match listener.accept().await {
            Ok(v) => v,
            Err(e) => { tracing::warn!(service = %svc.name, "accept: {e}"); continue; }
        };
        let Ok(permit) = shared.semaphore.clone().try_acquire_owned() else {
            continue; // rejected_overload
        };
        let shared = Arc::clone(&shared);
        let svc = svc.clone();
        tokio::spawn(async move {
            let _ = handle_client(stream, peer, &svc, &shared).await;
            drop(permit);
        });
    }
}
```

### 5. Banner + snip

```rust
tokio::time::timeout(shared.idle, stream.write_all(svc.banner.as_bytes())).await??;
// log banner_sent
let mut buf = vec![0u8; shared.read_limit];
match tokio::time::timeout(shared.idle, stream.read(&mut buf)).await {
    Ok(Ok(0)) => { /* client_close */ }
    Ok(Ok(n)) => { /* classify_event + log */ }
    Err(_) => { /* idle_timeout */ }
    Ok(Err(e)) => return Err(e.into()),
}
```

### 6. Main

```rust
#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // load TOML, bind each service, spawn accept_loop
    tokio::signal::ctrl_c().await?;
    Ok(())
}
```

### 7. Verify

```bash
cargo build --release
./target/release/honeyshop-trap crates/honeyshop-trap/config.example.toml
curl -v --max-time 2 http://127.0.0.1:8080/ || true
grep '"trap":"rust"' logs/honeyshop.jsonl | tail
```

### 8. Do not change

- JSONL contract / Python API / WS / eBPF / UI

### 9. Optional later

- Cargo features: `std-threads` vs `tokio` for dual CI
- Per-IP rate window after tokio is stable
