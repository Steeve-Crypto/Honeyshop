/** Shared types, demo data, and API helpers for Honeyshop UI */

export type Interaction = {
  timestamp: string;
  service: "ssh" | "http" | "ftp" | string;
  src_ip: string;
  src_port: number;
  event: string;
  data?: string;
  decoy?: boolean;
  trap?: string;
};

export type ServiceStatus = {
  name: string;
  port: number;
  enabled: boolean;
  hits: number;
};

export type AlertItem = {
  id: string;
  severity: "high" | "medium" | "low";
  title: string;
  detail: string;
  time: string;
};

export type Features = {
  ok?: boolean;
  api?: boolean;
  stream?: { up?: boolean; url?: string; cli?: string };
  engine?: { listeners_up?: boolean; services?: ServiceStatus[]; cli?: string; note?: string };
  rust_trap?: { cli?: string; note?: string };
  decoy?: { controllable?: boolean; running?: boolean; dir?: string };
  alerts?: { slack?: boolean; email?: boolean; enabled?: boolean };
  ebpf?: {
    available?: boolean;
    reason?: string;
    ui_toggle?: boolean;
    cli?: string;
    note?: string;
  };
  limits?: string[];
};

export type RuntimeConfig = {
  slack_webhook?: string;
  slack_configured?: boolean;
  smtp_host?: string;
  smtp_port?: number;
  smtp_user?: string;
  smtp_password?: string;
  smtp_configured?: boolean;
  email_from?: string;
  email_to?: string;
  log_file?: string;
  decoy_dir?: string;
  ports?: Record<string, number>;
  api_host?: string;
  api_port?: number;
  ws_port?: number;
};

export const API_BASE =
  (typeof import.meta !== "undefined" &&
    (import.meta as any).env?.PUBLIC_HONEYSHOP_API) ||
  "http://127.0.0.1:8787";

export const WS_URL =
  (typeof import.meta !== "undefined" &&
    (import.meta as any).env?.PUBLIC_HONEYSHOP_WS) ||
  "ws://127.0.0.1:8788/ws/interactions";

export const demoInteractions: Interaction[] = [
  {
    timestamp: new Date(Date.now() - 12000).toISOString(),
    service: "ssh",
    src_ip: "185.220.101.42",
    src_port: 44122,
    event: "banner_sent",
    data: "SSH-2.0-libssh2_1.10.0",
  },
  {
    timestamp: new Date(Date.now() - 45000).toISOString(),
    service: "http",
    src_ip: "45.33.32.156",
    src_port: 51880,
    event: "http_request",
    data: "GET /wp-login.php HTTP/1.1",
  },
  {
    timestamp: new Date(Date.now() - 90000).toISOString(),
    service: "ftp",
    src_ip: "103.149.28.17",
    src_port: 39211,
    event: "login_attempt",
    data: "USER admin / PASS ****",
  },
  {
    timestamp: new Date(Date.now() - 150000).toISOString(),
    service: "ssh",
    src_ip: "185.220.101.42",
    src_port: 44123,
    event: "client_data",
    data: "SSH-2.0-PuTTY_Release_0.78",
  },
  {
    timestamp: new Date(Date.now() - 210000).toISOString(),
    service: "http",
    src_ip: "91.134.187.20",
    src_port: 60321,
    event: "http_request",
    data: "GET /.env HTTP/1.1",
  },
  {
    timestamp: new Date(Date.now() - 300000).toISOString(),
    service: "ssh",
    src_ip: "198.51.100.23",
    src_port: 22001,
    event: "connection_closed",
  },
];

export const demoServices: ServiceStatus[] = [
  { name: "ssh", port: 2222, enabled: true, hits: 1284 },
  { name: "http", port: 8080, enabled: true, hits: 892 },
  { name: "ftp", port: 2121, enabled: true, hits: 341 },
];

export const demoAlerts: AlertItem[] = [
  {
    id: "1",
    severity: "high",
    title: "Suspicious payload",
    detail: "wget / Mirai-like string from 45.33.32.156",
    time: "2m ago",
  },
  {
    id: "2",
    severity: "medium",
    title: "High volume source IP",
    detail: "185.220.101.42 >= 20 interactions in 5m (SSH)",
    time: "8m ago",
  },
  {
    id: "3",
    severity: "medium",
    title: "Login attempts",
    detail: "Multiple FTP USER/PASS probes from 103.149.28.17",
    time: "14m ago",
  },
  {
    id: "4",
    severity: "low",
    title: "Service spike",
    detail: "HTTP service crossed baseline volume",
    time: "31m ago",
  },
];

export const demoFeatures: Features = {
  ok: true,
  api: false,
  stream: { up: false, url: WS_URL, cli: "python -m honeyshop.stream" },
  engine: {
    listeners_up: false,
    services: demoServices,
    cli: "python -m honeyshop",
    note: "Service ports bind in the engine process, not the browser",
  },
  decoy: { controllable: true, running: false, dir: "logs/decoy" },
  alerts: { slack: false, email: false, enabled: false },
  ebpf: {
    available: false,
    reason: "demo mode — API offline",
    ui_toggle: false,
    cli: "sudo python -m honeyshop --ebpf",
    note: "Needs root + bpftrace on the engine process; not UI-toggleable",
  },
  limits: [
    "eBPF requires root + bpftrace on the engine process",
    "Binding privileged/service ports is host process only",
    "ELK deploy is separate (compose override)",
  ],
};

export function summarize(interactions: Interaction[]) {
  const byService: Record<string, number> = {};
  const byIp: Record<string, number> = {};
  for (const i of interactions) {
    byService[i.service] = (byService[i.service] || 0) + 1;
    byIp[i.src_ip] = (byIp[i.src_ip] || 0) + 1;
  }
  const topIps = Object.entries(byIp).sort((a, b) => b[1] - a[1]).slice(0, 5);
  return { total: interactions.length, byService, topIps };
}

export function formatTime(iso: string) {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers || {}),
      },
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export async function getHealth() {
  return fetchJson<{ ok: boolean }>("/api/health");
}

export async function getOverview() {
  return fetchJson<{
    services: ServiceStatus[];
    alerts: AlertItem[];
    recent: Interaction[];
    total_hits: number;
    unique_sources: number;
    status: Record<string, unknown>;
    features?: Features;
  }>("/api/overview");
}

export async function getFeatures() {
  return fetchJson<Features>("/api/features");
}

export async function getInteractions(limit = 80) {
  return fetchJson<{ items: Interaction[]; count: number }>(
    `/api/interactions?limit=${limit}`,
  );
}

export async function getServices() {
  return fetchJson<{ items: ServiceStatus[] }>("/api/services");
}

export async function getAlerts() {
  return fetchJson<{ items: AlertItem[] }>("/api/alerts");
}

export async function getConfig() {
  return fetchJson<RuntimeConfig>("/api/config");
}

export async function saveConfig(body: Record<string, unknown>) {
  return fetchJson<{ ok: boolean; changed?: string[]; config?: RuntimeConfig; error?: string }>(
    "/api/config",
    { method: "POST", body: JSON.stringify(body) },
  );
}

export async function controlAction(action: "start_decoy" | "stop_decoy" | "test_alert") {
  return fetchJson<Record<string, unknown>>("/api/control", {
    method: "POST",
    body: JSON.stringify({ action }),
  });
}
