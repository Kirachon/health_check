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

## 9) Add your first monitored device (Agent) ✅

The dashboard shows **devices** only after you register a device and run an agent that heartbeats using that device token.

### Option A (Recommended / Default): Admin-only enrollment

This is the default mode (`DEVICE_REGISTRATION_MODE=admin`): agents **cannot** self-register. An admin registers the device and then copies `device_id` + `device_token` into the agent config.

#### A1) Register a device (creates `device_id` + `device_token`)

From the repo root:

```powershell
$ErrorActionPreference = "Stop"
$base = "http://localhost:8001/api/v1"

# Login (admin credentials)
$login = Invoke-RestMethod -Method Post -Uri "$base/auth/login" -ContentType "application/json" -Body (@{
  username = "admin"
  password = "change-me"
} | ConvertTo-Json)

$access = $login.access_token

# Register a device (replace hostname/ip)
$device = Invoke-RestMethod -Method Post -Uri "$base/devices/register" -Headers @{ Authorization = "Bearer $access" } -ContentType "application/json" -Body (@{
  hostname = "$env:COMPUTERNAME"
  ip       = "127.0.0.1"
  os       = "windows"
} | ConvertTo-Json)

$device
```

You will see output containing:
- `device_id`
- `token`

Save them somewhere secure (password manager is best).

#### A2) Configure and run the agent

From the repo root:

```powershell
Set-Location .\agent

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

Copy-Item .\config.yaml .\config.local.yaml
notepad .\config.local.yaml
```

Edit `agent\config.local.yaml`:

- `api_url: http://localhost:8001`
- `server_url: http://localhost:9090`
- `device_id: "<PASTE device_id HERE>"`
- `device_token: "<PASTE token HERE>"`

Then run the agent:

```powershell
.\.venv\Scripts\python.exe .\main.py
```

Within ~30–60 seconds the device should show as **Online** in the GUI dashboard.

## 10) Add another computer (remote device) ✅

To monitor a different computer on your network (not the server running the API):

### What must be reachable over the network

From the remote computer, the agent must be able to reach:

- **API** (`api_url`) — default: `http://<SERVER_IP>:8001`
- **VictoriaMetrics** (`server_url`) — default: `http://<SERVER_IP>:9090`

Important: in this repo the Docker ports are bound to `127.0.0.1` by default for safety, which means **other computers cannot reach them** until you intentionally expose them to your LAN.

### Step A) Expose the required ports to your internal network (server machine)

Do this only on a trusted internal/department network, and restrict access with Windows Firewall.

1) Edit `docker-compose.yml` on the server machine:

- Change VictoriaMetrics from:
  - `127.0.0.1:9090:8428`
  to:
  - `0.0.0.0:9090:8428`

2) Ensure the API is listening on the LAN:

- If you start it like this, it is **localhost-only** (recommended when you only monitor the same machine):
  - `--host 127.0.0.1`
- For remote agents, start it like this:
  - `--host 0.0.0.0`

3) Restart services:

```powershell
Set-Location C:\path\to\health_check   # adjust
docker compose up -d
```

Restart the API server with `--host 0.0.0.0` if needed.

4) Windows Firewall: allow only your internal subnet to these ports:

- TCP `8001` (API)
- TCP `9090` (VictoriaMetrics)

### Step B) Register the remote device (server machine, as admin)

Run on the server machine:

```powershell
$ErrorActionPreference = "Stop"
$base = "http://localhost:8001/api/v1"

$login = Invoke-RestMethod -Method Post -Uri "$base/auth/login" -ContentType "application/json" -Body (@{
  username = "admin"
  password = "change-me"
} | ConvertTo-Json)

$access = $login.access_token

# Replace these with the remote machine details
$remoteHostname = "REMOTE-PC-NAME"
$remoteIp = "192.168.1.50"

$device = Invoke-RestMethod -Method Post -Uri "$base/devices/register" -Headers @{ Authorization = "Bearer $access" } -ContentType "application/json" -Body (@{
  hostname = $remoteHostname
  ip       = $remoteIp
  os       = "windows"
} | ConvertTo-Json)

$device
```

Copy the returned `device_id` and `token` securely to the remote machine administrator.

### Step C) Install and run the agent on the remote machine

On the remote machine:

1) Copy the `agent/` folder (for example: zip it, SMB share, or internal Git clone).
2) Create `agent/config.local.yaml` and set:
   - `api_url: http://<SERVER_IP>:8001`
   - `server_url: http://<SERVER_IP>:9090`
   - `device_id: "<device_id from Step B>"`
   - `device_token: "<token from Step B>"`
3) Run:

```powershell
Set-Location C:\path\to\agent   # adjust
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .\config.yaml .\config.local.yaml
notepad .\config.local.yaml
.\.venv\Scripts\python.exe .\main.py
```

Back on the server machine, the GUI dashboard should show the remote device and it should become **Online** once heartbeats arrive.

### Option B (Labs only): Token-based self-enrollment

Use this only in trusted/internal lab environments. In this mode the agent can register itself using a shared registration token.

1. Set in `server\.env`:
   - `DEVICE_REGISTRATION_MODE=token`
   - `DEVICE_REGISTRATION_TOKEN=<a long random token>`
2. Restart the API.
3. Put the same value into `agent\config.local.yaml` as `registration_token: "<token>"`.
4. Run `agent\main.py` once; it will call `/devices/register` and write `device_id/device_token` into `config.local.yaml`.

## 10) Verify everything is working

- Docker stack:
  - `docker compose ps`
- API:
  - `http://localhost:8001/api/v1/health`
- GUI:
  - `http://localhost:5173`
- Grafana:
  - `http://localhost:3001`
- Device status:
  - GUI dashboard should show your device `Online` with a recent “last seen”.

## 11) Stopping / restarting (beginner friendly)

Stop the GUI dev server: press `Ctrl+C` in the GUI terminal.

Stop the API server: press `Ctrl+C` in the API terminal.

Stop Docker services:

```powershell
Set-Location C:\path\to\health_check   # adjust
docker compose down
```

## Troubleshooting (common beginner issues)

- **Docker isn’t running**: open Docker Desktop and wait until it says “Running”, then re-run `docker compose up -d`.
- **Grafana loops/restarts**: check `docker logs --tail 200 health_monitor_grafana` (often provisioning YAML errors or missing env vars).
- **UI says “Failed to fetch devices”**: confirm the API is running and reachable at `http://localhost:8001` and you are logged in.
- **Agent on Windows fails to start as a service**: avoid Microsoft Store Python. Use python.org Python and follow the service steps in `docs/deployment/windows.md`.

If you need to run the agent/API as Windows services (NSSM), use:
- `docs/deployment/windows.md`
