# Security & Data Leakage Review (Internal Networks)

This project is designed for **server/department networks only**. It should not require cloud services or outside connections.

## Threat Model (Practical)

**Attacker profiles**
- Untrusted host on the same LAN/VLAN (lateral movement, port scanning).
- Compromised workstation running the GUI (token theft, browser compromise).
- Compromised monitored host (agent token theft, spoofed heartbeats).
- Insider with access to configs/logs/containers.

**Trust boundaries**
- **Agent → API**: device registration + heartbeat (auth required).
- **Agent → VictoriaMetrics**: OTLP metrics export (treat metrics as sensitive).
- **GUI → API**: admin actions, device inventory, commands (JWT bearer tokens).
- **Grafana/Alertmanager → API**: webhook ingestion (token required).
- **API → Postgres**: all stored data (devices/users/alerts/etc.).

## Primary Data-Leak Vectors & Mitigations

### 1) Exposed service ports (P0/P1 depending on exposure)
**Risk:** If `5433` (Postgres), `9090` (VictoriaMetrics), `3001` (Grafana), or `9094` (Alertmanager) are reachable from untrusted networks, sensitive telemetry and credentials can leak.

**Mitigation:**
- Default `docker-compose.yml` binds these ports to `127.0.0.1` (local only).
- If you must expose them internally, restrict via firewall/VLAN and/or reverse proxy auth.

### 2) Default / hardcoded credentials (P0)
**Risk:** Known credentials (`admin/admin`, `monitor_pass`) enable immediate compromise.

**Mitigation:**
- Provide strong secrets via environment variables / `.env` (never commit).
- Rotate secrets before distribution.

### 3) Device identity spoofing (P0)
**Risk:** Unauthenticated heartbeats allow any LAN host to mark devices “online” and hide outages.

**Mitigation:**
- Require `X-Device-Token` for `POST /api/v1/devices/{device_id}/heartbeat`.
- Optionally require `X-Registration-Token` for `POST /api/v1/devices/register`.

### 4) Credentials accidentally committed (P0)
**Risk:** Device tokens in git history can be reused to impersonate devices.

**Mitigation:**
- Store per-machine credentials in `agent/config.local.yaml` (gitignored).
- Keep `agent/config.yaml` as a non-secret template.
- If you ever committed secrets, rotate them and rewrite history if needed (last resort).

### 5) Browser token storage (P1)
**Risk:** Access/refresh tokens in `localStorage` can be stolen by XSS/malicious extensions.

**Mitigation options:**
- Minimum: serve GUI via HTTPS, enable a strict CSP in your reverse proxy, and avoid inline scripts.
- Stronger: switch auth to HttpOnly cookies (requires a larger refactor).

## Secure-by-Default Baseline (Recommended)

- **Network**
  - Keep Postgres/VictoriaMetrics/Grafana/Alertmanager bound to localhost on the server.
  - Expose only `80/443` via reverse proxy if you need remote UI access.
  - Block direct access to `5433`, `9090`, `3001`, `9094`, `8001` from untrusted networks.

- **Secrets**
  - Set these at minimum:
    - `SECRET_KEY` (API JWT)
    - `POSTGRES_PASSWORD` (Docker)
    - `GRAFANA_ADMIN_PASSWORD` (Docker)
    - `ALERT_WEBHOOK_TOKEN` (Grafana → API webhook)
    - `DEVICE_REGISTRATION_TOKEN` (agents)
  - Rotate tokens/passwords before distributing to other teams.

- **API hardening**
  - Keep `DEBUG=False` in production.
  - Restrict `BACKEND_CORS_ORIGINS` to your GUI origin(s) only.

