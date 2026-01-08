# Health Monitoring System

> Internal-first monitoring system for servers and devices built with VictoriaMetrics, FastAPI, and React.

**Repository:** https://github.com/Kirachon/health_check

## Project Status

✅ **Ready for internal deployment** (server/department networks; no cloud required)

## Quick Start

### Prerequisites
- Docker + Docker Compose (or Docker Desktop on Windows)
- Python 3.11+ (server + agent)
- Node.js 20.19+ or 22.12+ (GUI) *(Vite 7 requires this; older Node may warn or fail to build)*

### 1. Start Infrastructure (Docker)

```bash
# Start all services (new CLI)
docker compose up -d

# Check service status
docker compose ps

# View logs
docker compose logs -f
```

**Services:**
- VictoriaMetrics: http://localhost:9090
- Grafana: http://localhost:3001 (admin/admin)
- Alertmanager: http://localhost:9094
- PostgreSQL: localhost:5433

Before starting in a shared environment, set the webhook token (used by Grafana → API alert ingestion):

Windows PowerShell:
```powershell
$env:ALERT_WEBHOOK_TOKEN = -join ((1..64) | ForEach-Object { '{0:x}' -f (Get-Random -Maximum 16) })
docker compose up -d
```

Linux/macOS:
```bash
export ALERT_WEBHOOK_TOKEN="$(openssl rand -hex 32)"
docker compose up -d
```
Keep `ALERT_WEBHOOK_TOKEN` secret (do not commit it; do not paste it into issue trackers or logs).
Tip: you can generate/store this token in a password manager instead of using shell history.
Alternative (cross-platform):
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Verify Setup

```bash
# Check VictoriaMetrics health
curl http://localhost:9090/health

# Check PostgreSQL connection
docker exec health_monitor_db psql -U monitor_user -d health_monitor -c "SELECT version();"
```

### 3. Access Grafana

1. Navigate to http://localhost:3001
2. Login with `admin` / `admin`
3. VictoriaMetrics datasource is pre-configured

### 4. Run Backend API

```bash
cd server
cp .env.example .env
python main.py
# Backend API: http://localhost:8001
```
Create an admin user before logging in:

Note: run these commands from the **repository root** (the same folder as `docker-compose.yml`).

Windows (PowerShell):
```powershell
./server/venv/Scripts/python.exe ./scripts/create_admin.py --username admin --password "<YOUR_STRONG_PASSWORD>" --role admin
```

Linux/macOS:
```bash
./server/venv/bin/python ./scripts/create_admin.py --username admin --password "<YOUR_STRONG_PASSWORD>" --role admin
```

### 5. Run Frontend (Optional)

```bash
cd gui
npm install
npm run dev
# Frontend UI: http://localhost:5173
```

## Troubleshooting (Quick)

- Grafana restarting in a loop: `docker logs --tail 200 health_monitor_grafana` (often alert provisioning YAML errors).
- API port in use: change `PORT` env var or stop the process bound to `8001`.
- UI can’t fetch devices: verify the API is reachable at `VITE_API_URL` and that you are logged in.

## Internal-Only Deployment Model

- This project is intended for server/department networks only.
- No cloud services are required.
- Restrict access with firewall rules / VLANs; do not expose Grafana/Postgres/VictoriaMetrics to the public internet.

## Onboarding More Servers (Agents)

To add another machine, install the agent on that machine and point it at your internal API + VictoriaMetrics:

1. Copy `agent/` to the target machine.
2. Edit `agent/config.yaml`:
   - `api_url: http://<YOUR-INTERNAL-API>:8001`
   - `server_url: http://<YOUR-VICTORIAMETRICS>:9090`
3. Run `agent/main.py` once (it registers and stores a device token).
4. Install as a service (systemd on Linux, NSSM on Windows).

## Key Features

- **Dashboard**: device inventory + online/offline status
- **Alerting**: Grafana → webhook → stored alert events, acknowledgements
- **Topology**: maps with device status and last-seen age
- **Discovery**: scan subnets and add discovered devices
- **Templates**: assign collections via templates/host groups (agent pulls config)

**Testing:** See [TESTING_GUIDE.md](./TESTING_GUIDE.md) for step-by-step manual testing

## Project Structure

```
health_check/
├── docker-compose.yml          # Infrastructure stack
├── config/
│   ├── postgres/
│   │   └── init.sql            # Database schema
│   ├── grafana/
│   │   └── provisioning/       # Datasources & dashboards
│   └── alertmanager/
│       └── alertmanager.yml    # Alert routing
├── server/                     # FastAPI backend (Phase 2)
├── agent/                      # Device monitoring agent (Phase 3)
└── gui/                        # React admin interface (Phase 4)
```

## Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Time-Series DB | VictoriaMetrics | Latest |
| API Server | FastAPI | 0.109+ |
| Database | PostgreSQL | 15 |
| Visualization | Grafana | Latest |

## License

Apache 2.0
