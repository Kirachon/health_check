# Health Monitor - Deployment Guide

## 📋 Overview

This guide covers deploying the Health Monitor system to production on Ubuntu/Debian servers.

## 🎯 New Port Configuration

All services use **non-standard ports** for security and conflict avoidance:

| Service | Port | Access URL |
|---------|------|------------|
| VictoriaMetrics | **9090** | http://localhost:9090 |
| PostgreSQL | **5433** | localhost:5433 |
| Grafana | **3001** | http://localhost:3001 |
| Alertmanager | **9094** | http://localhost:9094 |
| FastAPI | **8001** | http://localhost:8001/docs |
| React GUI | **5174** (dev) | http://localhost:5174 |

**Production (via Nginx):** All services accessible through `https://yourdomain.com`

---

## 🚀 Quick Deployment (Automated)

### Prerequisites
- Ubuntu 20.04+ or Debian 11+
- Root access
- Domain name pointing to server
- Ports 80, 443 open in firewall

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
nano config.yaml
# Update server_url to point to your production server
```

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

### Step 6: Start Docker Services

```bash
cd /opt/health-monitor
sudo docker-compose up -d

# Verify services
sudo docker-compose ps
```

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

### Step 9: Obtain SSL Certificate

```bash
# Using Let's Encrypt (free)
sudo certbot --nginx -d yourdomain.com

# Certificate auto-renewal is configured automatically
```

### Step 10: Set Permissions

```bash
sudo chown -R health-monitor:health-monitor /opt/health-monitor
sudo chmod -R 750 /opt/health-monitor
```

---

## 🔒 Security Hardening

### 1. Change Default Passwords

```bash
# PostgreSQL
sudo docker exec -it health_monitor_db psql -U monitor_user -d health_monitor
ALTER USER monitor_user WITH PASSWORD 'new-secure-password';
\q

# Update server/.env with new password
```

### 2. Set Admin Credentials

Create the initial admin user via `scripts/create_admin.py` and store credentials securely.
If upgrading, run the script if no admin accounts exist.

### 3. Lock Down Grafana

- Set `GF_SECURITY_ADMIN_USER` and `GF_SECURITY_ADMIN_PASSWORD` to strong values.
- Ensure Grafana is not exposed outside internal networks.

### 4. Configure Alert Webhook Token

- Set `ALERT_WEBHOOK_TOKEN` in `server/.env` and in the Grafana service environment.
- Rotate the token before distributing to other departments.

### 5. Configure Firewall

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

### 6. Secure JWT Secret

Generate a strong secret key (already done in automated install):

```bash
openssl rand -hex 32
```

Add to `server/.env`:
```
SECRET_KEY=your-generated-secret-key-here
```

### 4. Enable Fail2Ban (Optional)

```bash
sudo apt-get install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

---

## 📊 Post-Deployment Verification

### 1. Check Service Health

```bash
# Docker services
sudo docker-compose ps

# Systemd services
sudo systemctl status health-monitor-api
sudo systemctl status health-monitor-agent

# Nginx
sudo systemctl status nginx
```

### 2. Test Endpoints

```bash
# API health
curl https://yourdomain.com/api/v1/health

# Grafana
curl https://yourdomain.com/grafana/api/health

# VictoriaMetrics
curl http://localhost:9090/health
```

### 3. Access Web Interfaces

- **Admin Dashboard:** https://yourdomain.com
- **API Documentation:** https://yourdomain.com/api/v1/docs
- **Grafana:** https://yourdomain.com/grafana

Create the initial admin via `scripts/create_admin.py` after deployment.

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
nano config.yaml
# Update:
server_url: "https://yourdomain.com/victoriametrics"
api_url: "https://yourdomain.com/api/v1"

# 6. Register device (first run)
sudo /opt/health-monitor/agent/venv/bin/python main.py
# Device token will be auto-generated and saved

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
cat /opt/health-monitor/agent/config.yaml

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
