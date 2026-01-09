# Windows Hybrid Quickstart (Beginner, Copy/Paste)

This is the simplest setup pattern for Windows beginners:

- **Docker** runs the infrastructure stack (Postgres + VictoriaMetrics + Grafana + Alertmanager)
- **Windows host** runs the FastAPI server (Python venv)
- **Windows host** runs the GUI in dev mode (Vite)

If you want a “production-like single URL” on Windows (GUI build + reverse proxy on `http://localhost:8080`), use `docs/deployment/windows.md` instead.

## 0) Install prerequisites

Install these (in this order):

1. **Git for Windows**
2. **Docker Desktop** (enable WSL2 backend if asked)
3. **Python 3.11+** (python.org installer recommended)
4. **Node.js 20.19+ or 22.12+** (required by Vite 7)

Open **PowerShell** and verify:

```powershell
git --version
docker --version
docker compose version
python --version
node --version
npm --version
```

## 1) Clone the repo

```powershell
git clone https://github.com/Kirachon/health_check.git
cd health_check
```

## 2) Create secrets for Docker (root `.env`)

From the repo root (`health_check\`):

```powershell
$ErrorActionPreference = "Stop"

$secrets = python -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_hex(16)); print('GRAFANA_ADMIN_PASSWORD=' + secrets.token_hex(16)); print('ALERT_WEBHOOK_TOKEN=' + secrets.token_hex(32))"
$secrets | Out-File -Encoding ascii .env
```

Important:
- Do **not** commit `.env`.
- If you ever leak it (chat/logs/git), rotate these values and restart services.

## 3) Start the Docker stack

```powershell
docker compose up -d
docker compose ps
```

Open Grafana:
- `http://localhost:3001`
- username: `admin`
- password: value of `GRAFANA_ADMIN_PASSWORD` in `.env`

## 4) Set up the backend (FastAPI) and configure `server\.env`

```powershell
Set-Location .\server

python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt

Copy-Item .env.example .env
```

Now wire the server config to your Docker secrets:

```powershell
$POSTGRES_PASSWORD = (Get-Content ..\.env | Select-String '^POSTGRES_PASSWORD=').Line.Split('=')[1]
$ALERT_WEBHOOK_TOKEN = (Get-Content ..\.env | Select-String '^ALERT_WEBHOOK_TOKEN=').Line.Split('=')[1]

(Get-Content .env) `
  -replace '^SECRET_KEY=.*', ('SECRET_KEY=' + (python -c "import secrets; print(secrets.token_hex(32))")) `
  -replace '^DATABASE_URL=.*', ('DATABASE_URL=postgresql://monitor_user:' + $POSTGRES_PASSWORD + '@localhost:5433/health_monitor') `
  -replace '^ALERT_WEBHOOK_TOKEN=.*', ('ALERT_WEBHOOK_TOKEN=' + $ALERT_WEBHOOK_TOKEN) `
  | Set-Content .env
```

## 5) Create the first admin user

Run this from the **repo root**:

```powershell
Set-Location ..
.\server\venv\Scripts\python.exe .\scripts\create_admin.py --username admin --password "change-me" --role admin
```

## 6) Start the API server

```powershell
Set-Location .\server
.\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8001
```

API docs:
- `http://localhost:8001/api/v1/docs`

If port `8001` is already in use:
- stop the existing process, or
- run with another port: `--port 8002`

## 7) Start the GUI (dev)

Open a **second** PowerShell window:

```powershell
Set-Location C:\path\to\health_check\gui   # adjust
npm install
npm run dev
```

UI:
- `http://localhost:5173`

Note: if `5173` is already taken, Vite will usually pick `5174` and print the URL in the terminal.

## 8) Login

Go to the GUI URL and login:
- username: `admin`
- password: whatever you used in step 5

## Troubleshooting (common beginner issues)

- **Docker isn’t running**: open Docker Desktop and wait until it says “Running”, then re-run `docker compose up -d`.
- **Grafana loops/restarts**: check `docker logs --tail 200 health_monitor_grafana` (often provisioning YAML errors or missing env vars).
- **UI says “Failed to fetch devices”**: confirm the API is running and reachable at `http://localhost:8001` and you are logged in.
- **Agent on Windows fails to start as a service**: avoid Microsoft Store Python. Use python.org Python and follow the service steps in `docs/deployment/windows.md`.

