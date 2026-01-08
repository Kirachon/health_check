# Health Monitor - Deployment Guide

## 📋 Overview

This guide covers deploying the Health Monitor system to production on Ubuntu/Debian servers.
For local development on Windows/macOS/Linux, follow `README.md` quick start.

> ⚠️ **CRITICAL SECURITY WARNING:** This project is intended for internal server/department networks only. Do not expose service ports (Postgres, VictoriaMetrics, Grafana) publicly.
>
> Only expose `80/443` via your reverse proxy. Block direct access to `5433` (Postgres), `9090` (VictoriaMetrics), `3001` (Grafana), and `9094` (Alertmanager).

## ✅ Supported Deployment Scenarios

- **Single machine (internal-only):** Docker stack + API + GUI on one host (Windows or Linux).
- **Central server + many agents:** Linux server runs Docker stack + API + GUI; agents run on Windows/Linux servers.
- **No-internet / restricted internet:** Works fully inside your network. For the strongest guarantee, enforce egress allow-listing at the firewall.

Not currently “turn-key” in this repo:
- **Everything-in-Docker (API+GUI containers)** as the only deployment method (API/GUI are run from the host in this guide).

Windows deployments:
- For a Windows-focused deployment guide (including a Docker reverse proxy for a single internal URL), see `docs/deployment/windows.md`.

## 📦 Air-Gapped / Offline Deployment (No Internet)

If your environment has no internet access:

- **Do not** use the `curl ... | bash` installer.
- Mirror this repo to an internal Git server **or** copy a source archive into your environment.
- Pre-stage dependencies from a machine with internet:
  - Docker images: `docker pull` the required images, then `docker save` them to a `.tar`, and `docker load` inside the offline environment.
  - GUI build: build `gui/dist` on a connected build machine and copy only `gui/dist` into the offline environment (recommended), or provide an internal npm registry / offline cache.

Production does **not** need `npm install` on the server if you ship `gui/dist` as a build artifact.

Required Docker images (from `docker-compose.yml`):
- `victoriametrics/victoria-metrics:latest`
- `postgres:15-alpine`
- `grafana/grafana:latest`
- `prom/alertmanager:latest`

Example export/import (run on a connected machine, then copy the `.tar` into the offline environment):
```bash
docker pull victoriametrics/victoria-metrics:latest postgres:15-alpine grafana/grafana:latest prom/alertmanager:latest
docker save -o health-monitor-images.tar victoriametrics/victoria-metrics:latest postgres:15-alpine grafana/grafana:latest prom/alertmanager:latest

# In the offline environment:
docker load -i health-monitor-images.tar
```

## 🎯 New Port Configuration

All services use **non-standard ports** for security and conflict avoidance:

| Service | Port | Access URL |
|---------|------|------------|
| VictoriaMetrics | **9090** | http://localhost:9090 |
| PostgreSQL | **5433** | localhost:5433 |
| Grafana | **3001** | http://localhost:3001 |
| Alertmanager | **9094** | http://localhost:9094 |
| FastAPI | **8001** | http://localhost:8001/docs |
| React GUI | **5173** (dev) | http://localhost:5173 |

**Production (via Nginx):** All services accessible through `https://yourdomain.com`

---

## 🚀 Quick Deployment (Automated)

### Prerequisites
- Ubuntu 20.04+ or Debian 11+
- Root access
- Domain name pointing to server
- Ports 80, 443 open in firewall
- Node.js 20.19+ or 22.12+ for building the GUI *(Vite 7 requirement)*

Note: this guide uses `docker-compose` on Ubuntu/Debian. If your system uses the newer plugin, replace with `docker compose`.

### One-Command Install

```bash
curl -fsSL https://raw.githubusercontent.com/Kirachon/health_check/main/deployment/install.sh | sudo bash
```

Or manual:

```bash
git clone https://github.com/Kirachon/health_check.git
cd health_check/deployment
sudo chmod +x install.sh
sudo ./install.sh
```

The script will:
1. Install dependencies (Python, Node, Docker, Nginx)
2. Create service user
3. Set up virtual environments
4. Start Docker services
5. Configure systemd services
6. Set up Nginx reverse proxy
7. Obtain SSL certificate (Let's Encrypt)

---

## 📦 Manual Deployment

## 🔐 Required Secrets (Do Not Commit)

The Docker stack and API require secrets. Provide them via environment variables or a root `.env` file on the server:

- `POSTGRES_PASSWORD` (Docker Postgres)
- `GRAFANA_ADMIN_PASSWORD` (Docker Grafana)
- `ALERT_WEBHOOK_TOKEN` (Grafana → API webhook ingestion)
- `SECRET_KEY` (FastAPI JWT secret, in `server/.env`)

Optional depending on enrollment mode:
- `DEVICE_REGISTRATION_MODE` (default: `admin`)
- `DEVICE_REGISTRATION_TOKEN` (required only when `DEVICE_REGISTRATION_MODE=token`)

### Step 1: System Preparation

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install dependencies
sudo apt-get install -y python3 python3-pip python3-venv nodejs npm nginx certbot python3-certbot-nginx docker.io docker-compose git

# Create service user
sudo useradd -r -s /bin/false health-monitor

# Create installation directory
sudo mkdir -p /opt/health-monitor
cd /opt/health-monitor
```

### Step 2: Clone Repository

```bash
sudo git clone https://github.com/Kirachon/health_check.git .
```

### Step 3: Backend Setup

```bash
cd /opt/health-monitor/server

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate

# Configure environment
cp .env.example .env

# Generate secure secret key
SECRET_KEY=$(openssl rand -hex 32)

# Edit .env file
sudo nano .env
# Update:
# - SECRET_KEY (use generated key)
# - DATABASE_URL (already set to port 5433)
# - VICTORIA_METRICS_URL (already set to port 9090)
# - ALERT_WEBHOOK_TOKEN (required if ALERT_WEBHOOK_REQUIRE_TOKEN=true; use a strong random token, e.g. 64 hex chars = 32 bytes)
# - DEVICE_REGISTRATION_MODE (recommended: `admin` for admin-only enrollment)
# - DEVICE_REGISTRATION_TOKEN (only if DEVICE_REGISTRATION_MODE=token)
```

### Step 4: Agent Setup

```bash
cd /opt/health-monitor/agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate

# Configure agent
cp config.yaml config.local.yaml
# config.yaml is the template; config.local.yaml is your local runtime config (gitignored) where secrets/tokens live.
nano config.local.yaml
# Update server_url to point to your production server
```

Always edit `config.local.yaml` (not `config.yaml`) on real deployments, and keep it out of source control.

### Step 5: Frontend Build

```bash
cd /opt/health-monitor/gui

# Install dependencies
npm install

# Create production .env
cp .env.example .env
nano .env
# Update:
# VITE_API_URL=https://yourdomain.com/api/v1
# VITE_VM_URL=https://yourdomain.com/victoriametrics

# Build for production
npm run build
```

This produces `gui/dist/`. In production, your reverse proxy (Nginx) should serve these static files and route API paths to FastAPI.

### Step 6: Start Docker Services

```bash
cd /opt/health-monitor
export POSTGRES_PASSWORD="$(openssl rand -hex 16)"
export GRAFANA_ADMIN_PASSWORD="$(openssl rand -hex 16)"
export ALERT_WEBHOOK_TOKEN="$(openssl rand -hex 32)"
sudo docker-compose up -d

# Verify services
sudo docker-compose ps
```

For persistence across reboots, put these values into `/opt/health-monitor/.env` (same directory as `docker-compose.yml`)
instead of relying on `export` in a single shell session.

By default, Docker ports are bound to `127.0.0.1` for safety (not reachable from other machines).
⚠️ Security note: changing a mapping from `127.0.0.1:PORT:PORT` to `0.0.0.0:PORT:PORT` exposes that service to your network. Do this only if required, and then firewall/VLAN restrict it to your internal subnets.

If you need other internal machines to reach these services, edit the `ports:` mappings in `docker-compose.yml`
and restrict access with firewall rules / VLANs.

### Step 7: Configure Systemd Services

```bash
# Install service files
sudo cp deployment/systemd/health-monitor-api.service /etc/systemd/system/
sudo cp deployment/systemd/health-monitor-agent.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable health-monitor-api
sudo systemctl enable health-monitor-agent

# Start services
sudo systemctl start health-monitor-api
sudo systemctl start health-monitor-agent

# Check status
sudo systemctl status health-monitor-api
sudo systemctl status health-monitor-agent
```

Windows note:
- If you need Windows services, use NSSM from the official distribution and point it at the agent/service executables.
- NSSM binaries are not shipped in this repository.

### Step 8: Configure Nginx

```bash
# Copy config
sudo cp deployment/nginx/health-monitor.conf /etc/nginx/sites-available/

# Update domain name
sudo sed -i 's/monitor.example.com/yourdomain.com/g' /etc/nginx/sites-available/health-monitor.conf

# Enable site
sudo ln -s /etc/nginx/sites-available/health-monitor.conf /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

This Nginx config serves the production GUI build from `/opt/health-monitor/gui/dist`.
If you previously used a Vite dev server proxy, run `npm run build` in `gui/`, then reload Nginx.

#### 🔄 Migration from Dev Proxy Setup

If you previously ran the GUI in production via a Vite dev server (or Nginx proxy to `localhost:5173/5174`), migrate to the supported production setup:
1. Stop the Vite dev server.
2. Build the GUI: `cd /opt/health-monitor/gui && npm run build`.
3. Ensure Nginx serves `/opt/health-monitor/gui/dist` (see `deployment/nginx/health-monitor.conf`).
4. Reload Nginx: `sudo systemctl reload nginx`.
5. Validate:
   - `test -f /opt/health-monitor/gui/dist/index.html`
   - `curl -I https://yourdomain.com/` returns `200` (or `302` to your login route)

### Step 9: Obtain SSL Certificate

```bash
# Using Let's Encrypt (free)
sudo certbot --nginx -d yourdomain.com

# Certificate auto-renewal is configured automatically
```

Internal networks often use an internal CA instead of Let's Encrypt. In that case, install your internal TLS cert/key
and update the SSL paths in `deployment/nginx/health-monitor.conf`.

### Step 10: Set Permissions

```bash
sudo chown -R health-monitor:health-monitor /opt/health-monitor
sudo chmod -R 750 /opt/health-monitor
```

---

## 🔒 Security Hardening

### Change Default Passwords

For a fresh install, set strong secrets **before the first** `docker-compose up -d`:

- `POSTGRES_PASSWORD` (Postgres init password)
- `GRAFANA_ADMIN_PASSWORD` (Grafana admin password)
- `ALERT_WEBHOOK_TOKEN` (required token for Grafana → API webhook)

If you already have a running instance and want to rotate the Postgres password:

```bash
sudo docker exec -it health_monitor_db psql -U monitor_user -d health_monitor
ALTER USER monitor_user WITH PASSWORD 'new-secure-password';
\q
```

Then update `server/.env` so the API uses the new password in `DATABASE_URL`.

Note: `POSTGRES_PASSWORD` in `docker-compose.yml` is mainly used for the **initial** database creation. If you already have a persisted volume, changing the env var alone will not change the live DB password (rotate it inside Postgres as shown above).

### Create the Initial Admin User (Required)

Run this once after the database is up and `server/.env` is configured:

Linux:
```bash
cd /opt/health-monitor/server
source venv/bin/activate
python ../scripts/create_admin.py --username admin --password "change-me" --role admin
deactivate
```

Windows:
```powershell
$INSTALL_PATH = "C:\health-monitor"  # adjust
Set-Location "$INSTALL_PATH\server"
.\venv\Scripts\python.exe ..\scripts\create_admin.py --username admin --password "change-me" --role admin
```

Store the credentials securely and rotate them immediately after first login.

### Lock Down Grafana

- Set `GF_SECURITY_ADMIN_USER` and `GF_SECURITY_ADMIN_PASSWORD` to strong values.
- Ensure Grafana is not exposed outside internal networks.

### Configure Alert Webhook Token

- Set `ALERT_WEBHOOK_TOKEN` in `server/.env` and in the Grafana service environment.
- Rotate the token before distributing to other departments.

### Configure Firewall

```bash
# UFW (Ubuntu)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Block direct access to service ports
sudo ufw deny 9090
sudo ufw deny 5433
sudo ufw deny 3001
sudo ufw deny 9094
sudo ufw deny 8001
```

### No-Internet Egress (Strongest “No Leak Outside” Control)

If you must guarantee the system cannot send data to the internet, enforce it at the firewall:

- Allow outbound only to **internal subnets** (your LAN/VLAN ranges).
- Optionally allow outbound to internal DNS/NTP if required.
- Block outbound to the public internet.

This control is stronger than any application-level setting.

### Secure JWT Secret

Generate a strong secret key (already done in automated install):

```bash
openssl rand -hex 32
```

Add to `server/.env`:
```
SECRET_KEY=your-generated-secret-key-here
```

### Enable Fail2Ban (Optional)

```bash
sudo apt-get install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

---

## 📊 Post-Deployment Verification

### Check Service Health

```bash
# Docker services
sudo docker-compose ps

# Systemd services
sudo systemctl status health-monitor-api
sudo systemctl status health-monitor-agent

# Nginx
sudo systemctl status nginx
```

### Test Endpoints

```bash
# API health
curl https://yourdomain.com/api/v1/health

# Grafana
curl https://yourdomain.com/grafana/api/health

# VictoriaMetrics
curl http://localhost:9090/health
```

### Access Web Interfaces

- **Admin Dashboard:** https://yourdomain.com
- **API Documentation:** https://yourdomain.com/api/v1/docs
- **Grafana:** https://yourdomain.com/grafana

---

## 🖥️ Agent Deployment (Monitored Devices)

### On Each Device to Monitor:

```bash
# 1. Install dependencies
sudo apt-get install python3 python3-pip python3-venv

# 2. Create directory
sudo mkdir -p /opt/health-monitor/agent
cd /opt/health-monitor/agent

# 3. Copy agent files
# (scp or download from repository)

# 4. Install Python packages
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate

# 5. Configure agent
cp config.yaml config.local.yaml
nano config.local.yaml
# config.yaml is the template; config.local.yaml is your local runtime config (gitignored) where secrets/tokens live.
# Update:
server_url: "https://yourdomain.com/victoriametrics"
api_url: "https://yourdomain.com/api/v1"

# 6. Register device (first run, only if token-based self-enrollment is enabled)
sudo /opt/health-monitor/agent/venv/bin/python main.py
# Device token will be auto-generated and saved (in config.local.yaml)

# 7. Install systemd service
sudo cp health-monitor-agent.service /etc/systemd/system/
sudo systemctl enable health-monitor-agent
sudo systemctl start health-monitor-agent
```

---

## 📈 Monitoring & Maintenance

### View Logs

```bash
# API logs
sudo journalctl -u health-monitor-api -f

# Agent logs
sudo journalctl -u health-monitor-agent -f

# Docker logs
sudo docker-compose logs -f victoriametrics
sudo docker-compose logs -f postgres
sudo docker-compose logs -f grafana
```

### Restart Services

```bash
# Restart API
sudo systemctl restart health-monitor-api

# Restart Docker stack
cd /opt/health-monitor
sudo docker-compose restart

# Reload Nginx
sudo systemctl reload nginx
```

### Database Backup

```bash
# Backup PostgreSQL
sudo docker exec health_monitor_db pg_dump -U monitor_user health_monitor > backup_$(date +%Y%m%d).sql

# Backup VictoriaMetrics
sudo docker exec health_monitor_vm /victoria-metrics-prod -storageDataPath=/victoria-metrics-data -snapshotCreateTimeout=30s -snapshot.createURL=http://localhost:8428/snapshot/create
```

### Update System

```bash
cd /opt/health-monitor
sudo git pull
sudo docker-compose pull
sudo docker-compose up -d
sudo systemctl restart health-monitor-api
sudo systemctl restart health-monitor-agent
```

---

## 🐛 Troubleshooting

### API Not Starting

```bash
# Check logs
sudo journalctl -u health-monitor-api -n 50

# Check database connection
sudo docker exec -it health_monitor_db psql -U monitor_user -d health_monitor

# Verify port availability
sudo netstat -tlnp | grep 8001
```

### Agent Not Connecting

```bash
# Check config
cat /opt/health-monitor/agent/config.local.yaml

# Test connectivity
curl https://yourdomain.com/api/v1/health

# Check logs
sudo journalctl -u health-monitor-agent -n 50
```

### Grafana Not Accessible

```bash
# Check if running
sudo docker ps | grep grafana

# Check logs
sudo docker logs health_monitor_grafana

# Restart
sudo docker-compose restart grafana
```

If Grafana is restarting in a loop, check provisioning errors (common causes: invalid YAML, missing alert rule `folder` in provisioned rule groups, or missing required environment variables like `ALERT_WEBHOOK_TOKEN`).

## 🪟 Windows Deployment Notes (Single Host)

For a Windows-focused deployment guide (including a Docker reverse proxy for a single internal URL), see `docs/deployment/windows.md`.

Quick outline (internal-only single-machine):

1. Start the Docker stack from the repo root (`POSTGRES_PASSWORD`, `GRAFANA_ADMIN_PASSWORD`, `ALERT_WEBHOOK_TOKEN` required).
2. Run the FastAPI server from `server\venv` (or install it as a Windows service).
3. Build the GUI (`gui\dist`).
4. (Recommended) Use the Docker reverse proxy overlay: `deployment/docker-compose.windows-proxy.yml` and access the app via `http://localhost:8080/`.

For Windows agents, use NSSM to run `agent\.venv\Scripts\python.exe agent\main.py` and store credentials in `agent/config.local.yaml`.

Example (PowerShell as Administrator, adjust paths):

```powershell
# Security note: only run binaries you trust. Verify the NSSM download is authentic before using it.
# If PowerShell blocks running scripts in your environment, you may need:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# (RemoteSigned allows local scripts; downloaded scripts must be signed. You can also just run these commands manually.)

# Create agent venv + install deps
$INSTALL_PATH = "C:\health-monitor"  # adjust
Set-Location "$INSTALL_PATH\agent"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Install service via NSSM (download from the official NSSM site and extract it somewhere on disk)
$NSSM_PATH = "C:\Tools\nssm\nssm.exe"  # adjust
& $NSSM_PATH install health-monitor-agent "$INSTALL_PATH\agent\.venv\Scripts\python.exe" "$INSTALL_PATH\agent\main.py"
& $NSSM_PATH set health-monitor-agent AppDirectory "$INSTALL_PATH\agent"

# Start
Start-Service -Name health-monitor-agent

# Verify
Get-Service -Name health-monitor-agent
```

---

## 📞 Support

- **Repository:** https://github.com/Kirachon/health_check
- **Issues:** https://github.com/Kirachon/health_check/issues
- **Documentation:** See README files in each component directory

---

## ✅ Deployment Checklist

- [ ] Domain configured and DNS pointing to server
- [ ] Firewall rules configured (80, 443 open)
- [ ] Services installed and running
- [ ] SSL certificate obtained
- [ ] Default passwords changed
- [ ] JWT secret key generated and set
- [ ] Agent deployed on monitored devices
- [ ] Grafana dashboards configured
- [ ] Alert notifications tested
- [ ] Backup strategy implemented
- [ ] Monitoring agents registered
- [ ] Security hardening complete
