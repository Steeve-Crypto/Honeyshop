# Aya for eBPF — decision

**Recommendation: not now.**

Honeyshop already has host signal via **bpftrace** (`honeyshop --ebpf`).

| | bpftrace (current) | Aya (Rust eBPF) |
|--|--------------------|-----------------|
| Ship | scripts + Python supervisor | nightly + bpf-linker + BTF |
| Binary | needs bpftrace installed | self-contained probe possible |
| Fit | matches dead-simple path | long-term Rust trap stack |
| UI | status + CLI enable | same — still needs CAP_BPF/root |

**When to add Aya:** after tokio trap is stable *and* you want one musl binary with embedded probes, no bpftrace dependency.

Until then keep bpftrace; Settings UI shows eBPF status.
