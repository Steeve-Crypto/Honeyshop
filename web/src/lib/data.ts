/** Shared types and sample data for Honeyshop UI */

export type Interaction = {
  timestamp: string;
  service: "ssh" | "http" | "ftp" | string;
  src_ip: string;
  src_port: number;
  event: string;
  data?: string;
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
