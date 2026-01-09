# No-Docker Deployment (Beginner Friendly, Internal-Only)

This guide shows how to deploy Health Monitor **without Docker** by installing the dependencies directly on the machine (onto the drive).

What you’ll run “natively”:
- FastAPI server (`server/`) ✅
- GUI (React) (`gui/`) ✅
- Agent (`agent/`) ✅ (on every monitored computer)

What Docker normally provides (you must install yourself):
- PostgreSQL (required)
- VictoriaMetrics (required)
- Grafana + Alertmanager (optional, but recommended for dashboards/alerts)

> Internal-only: this project is designed for server/department networks. Do not expose Postgres/VictoriaMetrics/Grafana publicly.

---

## Target Ports (defaults)

You can change these, but keep them consistent across configs:

- FastAPI: `8001`
- PostgreSQL: `5432` (Docker setup used `5433`; native usually uses `5432`)
- VictoriaMetrics: `9090`
- Grafana: `3000` (Docker setup used `3001`; native usually uses `3000`)
- Alertmanager: `9093` (Docker setup used `9094`; native usually uses `9093`)

---

## Step 1 — Install PostgreSQL (required)

### Windows

1. Install PostgreSQL 15+ (official installer).
2. Set a strong password for the database superuser (keep it safe).
3. Open “SQL Shell (psql)” or `psql` and create the app DB/user:

```sql
CREATE USER monitor_user WITH PASSWORD 'CHANGE_ME_STRONG';
CREATE DATABASE health_monitor OWNER monitor_user;
```

### Linux (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib
```

Create DB/user:

```bash
sudo -u postgres psql <<'SQL'
CREATE USER monitor_user WITH PASSWORD 'CHANGE_ME_STRONG';
CREATE DATABASE health_monitor OWNER monitor_user;
SQL
```

---

## Step 2 — Install VictoriaMetrics (required)

VictoriaMetrics is a single binary you run as a service.

Goal:
- Listen on `http://localhost:9090`
- Store data on disk (choose a folder you will back up)

### Windows

1. Download the VictoriaMetrics release for Windows and extract it.
2. Create a data folder, for example: `C:\health-monitor\data\victoria-metrics`
3. Run it (example):

```powershell
& "C:\path\to\victoria-metrics-prod.exe" `
  --storageDataPath="C:\health-monitor\data\victoria-metrics" `
  --httpListenAddr=":9090" `
  --retentionPeriod=12
```

For “always on”, run it as a service (NSSM) or scheduled task.

### Linux (Ubuntu/Debian)

1. Download and unpack VictoriaMetrics for Linux (the “victoria-metrics-prod” binary).
2. Create data dir:

```bash
sudo mkdir -p /var/lib/victoria-metrics
sudo chown -R $(whoami):$(whoami) /var/lib/victoria-metrics
```

3. Run it:

```bash
./victoria-metrics-prod \
  --storageDataPath=/var/lib/victoria-metrics \
  --httpListenAddr=:9090 \
  --retentionPeriod=12
```

For production, install it as a systemd service.

Quick health check:
```bash
curl http://localhost:9090/health
```

---

## Step 3 — Install Grafana + Alertmanager (optional but recommended)

If you skip this, the core monitoring (API + VM + agents) still works, but you won’t have Grafana dashboards/alert UI.

### Grafana

Install Grafana and start it.

Important:
- Set a strong admin password.
- Point the VictoriaMetrics data source at `http://localhost:9090`.

Optional provisioning:
This repo includes provisioning files under `config/grafana/provisioning`. If you want the repo’s dashboards/datasources preloaded, copy that folder into Grafana’s provisioning directory for your OS and restart Grafana.

### Alertmanager

Install Alertmanager and configure it with:
- `config/alertmanager/alertmanager.yml` (from this repo)

---

## Step 4 — Configure and run the FastAPI server (required)

### Windows

From the repo root:

```powershell
Set-Location .\server
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt

Copy-Item .env.example .env
notepad .env
```

Set these values in `server\.env`:

- `DATABASE_URL=postgresql://monitor_user:<DB_PASSWORD>@localhost:5432/health_monitor`
- `VICTORIA_METRICS_URL=http://localhost:9090`
- `SECRET_KEY=<random 64-hex string>`
- `ALERT_WEBHOOK_TOKEN=<random token>` (if you use Grafana webhook ingestion)

Start API:
```powershell
.\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8001
```

### Linux

```bash
cd server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env

uvicorn main:app --host 0.0.0.0 --port 8001
```

API docs:
- `http://localhost:8001/api/v1/docs`

---

## Step 5 — Create the first admin user (required)

From the repo root:

Windows:
```powershell
.\server\venv\Scripts\python.exe .\scripts\create_admin.py --username admin --password "change-me" --role admin
```

Linux:
```bash
./server/venv/bin/python ./scripts/create_admin.py --username admin --password "change-me" --role admin
```

---

## Step 6 — Run the GUI

### Dev (beginner friendly)

```powershell
cd gui
npm install
npm run dev
```

UI:
- `http://localhost:5173`

### Production-like

Build the GUI:
```bash
cd gui
npm install
npm run build
```

Then serve `gui/dist` with an internal web server (IIS/Nginx/etc). If you want a single-URL reverse proxy setup, see:
- Windows: `docs/deployment/windows.md`
- Linux: `DEPLOYMENT.md`

---

## Step 7 — Add other computers (install agents)

On each computer you want to monitor:

1. Copy the `agent/` folder onto the target machine.
2. Create `agent/config.local.yaml`:
   - copy `agent/config.yaml` → `agent/config.local.yaml`
   - set:
     - `api_url: http://<SERVER_IP>:8001`
     - `server_url: http://<SERVER_IP>:9090`
3. Get `device_id` + `device_token` from the server (admin creates device) and paste into `config.local.yaml`.
4. Run the agent:

```powershell
cd agent
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\main.py
```

The device should appear and turn Online once heartbeats arrive.

---

## Common gotchas (no-Docker)

- If you used the Docker setup before, your ports/passwords may differ (`5433` vs `5432`, `3001` vs `3000`, `9094` vs `9093`). Update `server/.env` accordingly.
- VictoriaMetrics must be reachable from agents if you want remote agents. If VM is bound to `localhost` only, remote agents can’t write metrics.
- Don’t commit secrets (`server/.env`, root `.env`, `agent/config.local.yaml`).

