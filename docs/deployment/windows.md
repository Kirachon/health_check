# Windows Deployment (Internal-Only)

This guide covers deploying Health Monitor on **Windows** (internal server/department networks only).

If you can choose, a Linux server is still the simplest “production” path (systemd + Nginx + certbot). Windows can run it reliably too, but you’ll typically want a reverse proxy layer to avoid CORS and to present a single URL.

## Prerequisites

- Windows 10/11 or Windows Server
- Docker Desktop (WSL2 backend recommended)
- Python 3.11+ (use the official python.org installer, not the Microsoft Store shim)
- (Optional) NSSM (Non-Sucking Service Manager) for running the API/agent as Windows services

## Option A (Recommended): Docker reverse proxy + Host API

This keeps “one URL” (GUI + API + Grafana + VictoriaMetrics) without IIS/ARR.

### Security notes (internal-only)

- The reverse proxy binds to `127.0.0.1:8080` by default (localhost-only). Keep it that way unless you also lock down Windows Firewall/VLANs.
- Treat the repo-root `.env` as a secret file. On Windows you can restrict it with NTFS ACLs (example):
  - `icacls .env /inheritance:r /grant:r "%USERNAME%:R" "%USERNAME%:W"`

### 1) Start the monitoring stack

From the repo root:

```powershell
$ErrorActionPreference = "Stop"
Set-Location C:\health-monitor   # adjust

# Create a root .env used by docker compose (DO NOT COMMIT)
$secrets = python -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_hex(16)); print('GRAFANA_ADMIN_PASSWORD=' + secrets.token_hex(16)); print('ALERT_WEBHOOK_TOKEN=' + secrets.token_hex(32))"
$secrets | Out-File -Encoding ascii .env

docker compose up -d
docker compose ps
```

### 2) Run the FastAPI server on the host

```powershell
Set-Location C:\health-monitor\server   # adjust
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt

Copy-Item .env.example .env

# Set secrets and point DB URL at the local Docker Postgres
$POSTGRES_PASSWORD = (Get-Content ..\.env | Select-String '^POSTGRES_PASSWORD=').Line.Split('=')[1]
$ALERT_WEBHOOK_TOKEN = (Get-Content ..\.env | Select-String '^ALERT_WEBHOOK_TOKEN=').Line.Split('=')[1]

(Get-Content .env) `
  -replace '^SECRET_KEY=.*', ('SECRET_KEY=' + (python -c "import secrets; print(secrets.token_hex(32))")) `
  -replace '^DATABASE_URL=.*', ('DATABASE_URL=postgresql://monitor_user:' + $POSTGRES_PASSWORD + '@localhost:5433/health_monitor') `
  -replace '^ALERT_WEBHOOK_TOKEN=.*', ('ALERT_WEBHOOK_TOKEN=' + $ALERT_WEBHOOK_TOKEN) `
  | Set-Content .env

.\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8001
```

### 3) Build the GUI and start the Windows proxy service

Build the GUI:

```powershell
Set-Location C:\health-monitor\gui   # adjust
npm install
npm run build
```

Start the Windows reverse proxy (Nginx in Docker) which serves `gui\dist` and proxies to host services:

```powershell
Set-Location C:\health-monitor   # adjust
docker compose -f docker-compose.yml -f deployment\docker-compose.windows-proxy.yml up -d
docker compose ps
```

Open:
- GUI: `http://localhost:8080/`
- API: `http://localhost:8080/api/v1/docs`
- Grafana: `http://localhost:8080/grafana/`
- VictoriaMetrics: `http://localhost:8080/victoriametrics/`

## Option B: IIS for GUI (advanced)

Use this only if you already manage IIS heavily. To avoid CORS issues, you’ll typically need IIS URL Rewrite + ARR (reverse proxy) so the GUI and API share the same origin.

If you want this approach, request it and we can add a `web.config` SPA fallback and ARR rewrite rules tailored to your exact URLs/ports.

## Running API/Agent as Windows Services (NSSM)

Download NSSM from the official site, extract it, then:

```powershell
$INSTALL_PATH = "C:\health-monitor"   # adjust
$NSSM_PATH = "C:\Tools\nssm\nssm.exe" # adjust

# API service
& $NSSM_PATH install health-monitor-api "$INSTALL_PATH\server\venv\Scripts\python.exe" "-m uvicorn main:app --host 127.0.0.1 --port 8001"
& $NSSM_PATH set health-monitor-api AppDirectory "$INSTALL_PATH\server"

# If you need other machines to reach the API directly, change `--host 127.0.0.1` to `--host 0.0.0.0`
# and then lock it down with Windows Firewall rules.

# Agent service
& $NSSM_PATH install health-monitor-agent "$INSTALL_PATH\agent\.venv\Scripts\python.exe" "$INSTALL_PATH\agent\main.py"
& $NSSM_PATH set health-monitor-agent AppDirectory "$INSTALL_PATH\agent"

Start-Service -Name health-monitor-api
Start-Service -Name health-monitor-agent
Get-Service -Name health-monitor-api,health-monitor-agent
```

Note: the agent reads `agent\config.local.yaml` by default. Keep it out of source control.
