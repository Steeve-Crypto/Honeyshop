//! honeyshop-trap — multi-port trap listeners (std only).
//! JSONL compatible with Python Honeyshop API + WebSocket stream.

use std::env;
use std::fs::{self, OpenOptions};
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpListener, TcpStream};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

fn main() {
    let config_path = env::args()
        .nth(1)
        .unwrap_or_else(|| "crates/honeyshop-trap/config.example.toml".into());

    let cfg = Config::load(&config_path).unwrap_or_else(|e| {
        eprintln!("config error: {e}");
        std::process::exit(1);
    });

    let log_path = PathBuf::from(&cfg.log_file);
    if let Some(parent) = log_path.parent() {
        let _ = fs::create_dir_all(parent);
    }

    let state = Arc::new(State {
        log_path,
        log_lock: Mutex::new(()),
        active: AtomicUsize::new(0),
        idle: Duration::from_secs(cfg.idle_timeout_secs.max(1)),
        read_limit: cfg.read_limit.max(64),
        max_connections: if cfg.max_connections == 0 {
            usize::MAX
        } else {
            cfg.max_connections
        },
    });

    eprintln!(
        "honeyshop-trap starting · log={} · max_conn={} · services={}",
        state.log_path.display(),
        state.max_connections,
        cfg.services.len()
    );

    let mut handles = Vec::new();
    for svc in cfg.services {
        let addr = format!("{}:{}", cfg.bind, svc.port);
        let listener = match TcpListener::bind(&addr) {
            Ok(l) => l,
            Err(e) => {
                eprintln!("bind {addr} ({}) failed: {e}", svc.name);
                std::process::exit(1);
            }
        };
        eprintln!("listening {} on {}", svc.name, addr);
        let state = Arc::clone(&state);
        handles.push(thread::spawn(move || accept_loop(listener, svc, state)));
    }

    for h in handles {
        let _ = h.join();
    }
}

struct State {
    log_path: PathBuf,
    log_lock: Mutex<()>,
    active: AtomicUsize,
    idle: Duration,
    read_limit: usize,
    max_connections: usize,
}

#[derive(Clone)]
struct ServiceCfg {
    name: String,
    port: u16,
    banner: String,
}

struct Config {
    log_file: String,
    bind: String,
    max_connections: usize,
    idle_timeout_secs: u64,
    read_limit: usize,
    services: Vec<ServiceCfg>,
}

impl Config {
    fn load(path: &str) -> Result<Self, String> {
        let text = fs::read_to_string(path).map_err(|e| format!("read {path}: {e}"))?;
        parse_toml_lite(&text)
    }
}

fn parse_toml_lite(text: &str) -> Result<Config, String> {
    let mut log_file = "logs/honeyshop.jsonl".to_string();
    let mut bind = "0.0.0.0".to_string();
    let mut max_connections = 10_000usize;
    let mut idle_timeout_secs = 15u64;
    let mut read_limit = 2048usize;
    let mut services = Vec::new();
    let mut in_service = false;
    let mut cur_name = String::new();
    let mut cur_port: u16 = 0;
    let mut cur_banner = String::new();

    let flush = |services: &mut Vec<ServiceCfg>, name: &mut String, port: &mut u16, banner: &mut String| {
        if !name.is_empty() && *port != 0 {
            services.push(ServiceCfg {
                name: name.clone(),
                port: *port,
                banner: banner.clone(),
            });
        }
        name.clear();
        *port = 0;
        banner.clear();
    };

    for raw in text.lines() {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        if line == "[[services]]" {
            if in_service {
                flush(&mut services, &mut cur_name, &mut cur_port, &mut cur_banner);
            }
            in_service = true;
            continue;
        }
        if let Some((k, v)) = line.split_once('=') {
            let k = k.trim();
            let v = unquote(v.trim());
            if in_service {
                match k {
                    "name" => cur_name = v,
                    "port" => cur_port = v.parse().unwrap_or(0),
                    "banner" => cur_banner = unescape_banner(&v),
                    _ => {}
                }
            } else {
                match k {
                    "log_file" => log_file = v,
                    "bind" => bind = v,
                    "max_connections" => max_connections = v.parse().unwrap_or(10_000),
                    "idle_timeout_secs" => idle_timeout_secs = v.parse().unwrap_or(15),
                    "read_limit" => read_limit = v.parse().unwrap_or(2048),
                    _ => {}
                }
            }
        }
    }
    if in_service {
        flush(&mut services, &mut cur_name, &mut cur_port, &mut cur_banner);
    }
    if services.is_empty() {
        return Err("no [[services]] defined".into());
    }
    Ok(Config {
        log_file,
        bind,
        max_connections,
        idle_timeout_secs,
        read_limit,
        services,
    })
}

fn unquote(s: &str) -> String {
    let s = s.trim();
    if s.len() >= 2 && s.starts_with('"') && s.ends_with('"') {
        s[1..s.len() - 1].to_string()
    } else {
        s.to_string()
    }
}

fn unescape_banner(s: &str) -> String {
    s.replace("\\r", "\r").replace("\\n", "\n").replace("\\t", "\t")
}

fn accept_loop(listener: TcpListener, svc: ServiceCfg, state: Arc<State>) {
    loop {
        let (stream, peer) = match listener.accept() {
            Ok(v) => v,
            Err(e) => {
                eprintln!("accept {} error: {e}", svc.name);
                continue;
            }
        };

        if state.active.load(Ordering::Relaxed) >= state.max_connections {
            let _ = log_event(&state, &svc.name, peer, "rejected_overload", "");
            continue;
        }

        let state = Arc::clone(&state);
        let svc = svc.clone();
        thread::spawn(move || {
            state.active.fetch_add(1, Ordering::Relaxed);
            if let Err(e) = handle_client(stream, peer, &svc, &state) {
                eprintln!("{} client {}: {e}", svc.name, peer);
            }
            state.active.fetch_sub(1, Ordering::Relaxed);
        });
    }
}

fn handle_client(
    mut stream: TcpStream,
    peer: SocketAddr,
    svc: &ServiceCfg,
    state: &State,
) -> Result<(), String> {
    let _ = stream.set_read_timeout(Some(state.idle));
    let _ = stream.set_write_timeout(Some(state.idle));

    stream
        .write_all(svc.banner.as_bytes())
        .map_err(|e| format!("write banner: {e}"))?;
    let _ = stream.flush();

    log_event(state, &svc.name, peer, "banner_sent", &truncate(&svc.banner, 256))?;

    let mut buf = vec![0u8; state.read_limit];
    match stream.read(&mut buf) {
        Ok(0) => log_event(state, &svc.name, peer, "client_close", "")?,
        Ok(n) => {
            let data = sanitize_payload(&buf[..n]);
            let event = classify_event(&svc.name, &data);
            log_event(state, &svc.name, peer, event, &data)?;
        }
        Err(e) if e.kind() == std::io::ErrorKind::WouldBlock || e.kind() == std::io::ErrorKind::TimedOut => {
            log_event(state, &svc.name, peer, "idle_timeout", "")?;
        }
        Err(e) => return Err(format!("read: {e}")),
    }
    Ok(())
}

fn classify_event(service: &str, data: &str) -> &'static str {
    let lower = data.to_ascii_lowercase();
    match service {
        "http" if lower.starts_with("get ") || lower.starts_with("post ") || lower.starts_with("head ") => {
            "http_request"
        }
        "ftp" if lower.starts_with("user ") || lower.starts_with("pass ") => "login_attempt",
        _ => "client_data",
    }
}

fn sanitize_payload(bytes: &[u8]) -> String {
    let s: String = bytes
        .iter()
        .map(|&b| {
            if (0x20..=0x7e).contains(&b) || b == b'\n' || b == b'\r' || b == b'\t' {
                b as char
            } else {
                '.'
            }
        })
        .collect();
    truncate(&s, 2048)
}

fn truncate(s: &str, max: usize) -> String {
    if s.len() <= max {
        s.to_string()
    } else {
        format!("{}…", &s[..max])
    }
}

fn now_rfc3339() -> String {
    let dur = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default();
    let secs = dur.as_secs() as i64;
    let days = secs.div_euclid(86400);
    let tod = secs.rem_euclid(86400) as u32;
    let (y, m, d) = civil_from_days(days + 719468);
    let hh = tod / 3600;
    let mm = (tod % 3600) / 60;
    let ss = tod % 60;
    format!("{y:04}-{m:02}-{d:02}T{hh:02}:{mm:02}:{ss:02}Z")
}

fn civil_from_days(z: i64) -> (i32, u32, u32) {
    let era = if z >= 0 { z } else { z - 146096 } / 146097;
    let doe = (z - era * 146097) as u64;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let y = yoe as i64 + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = if m <= 2 { y + 1 } else { y };
    (y as i32, m as u32, d as u32)
}

fn json_escape(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 8);
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if c.is_control() => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out
}

fn log_event(
    state: &State,
    service: &str,
    peer: SocketAddr,
    event: &str,
    data: &str,
) -> Result<(), String> {
    let line = format!(
        "{{\"timestamp\":\"{}\",\"level\":\"INFO\",\"logger\":\"honeyshop.trap\",\"message\":\"interaction\",\"service\":\"{}\",\"src_ip\":\"{}\",\"src_port\":{},\"event\":\"{}\",\"data\":\"{}\",\"trap\":\"rust\"}}\n",
        now_rfc3339(),
        json_escape(service),
        json_escape(&peer.ip().to_string()),
        peer.port(),
        json_escape(event),
        json_escape(data),
    );
    let _guard = state
        .log_lock
        .lock()
        .map_err(|_| "log lock poisoned".to_string())?;
    append_file(&state.log_path, line.as_bytes())
}

fn append_file(path: &Path, bytes: &[u8]) -> Result<(), String> {
    let mut f = OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)
        .map_err(|e| format!("open log: {e}"))?;
    f.write_all(bytes).map_err(|e| format!("write log: {e}"))?;
    Ok(())
}
