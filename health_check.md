1️⃣ System Overview (Blueprint Level)
Core Principle

Each device monitors itself → sends data to a central server → GUI visualizes everything

Architecture Style

Agent-based

Centralized control plane

Push model (secure, scalable)

2️⃣ Component Blueprint (Authoritative)
┌────────────────────────────────────────────┐
│                Admin GUI                   │
│  (Desktop or Web Application)               │
│                                            │
│  - Admin Login                              │
│  - Device List                              │
│  - Device Health Dashboard                 │
│  - Alerts & History                        │
└───────────────┬────────────────────────────┘
                │ HTTPS (REST)
                ▼
┌────────────────────────────────────────────┐
│          Central Monitoring Server          │
│                                            │
│  API Layer                                  │
│  ├─ Auth (Admin & Device Tokens)            │
│  ├─ Device Registration                    │
│  ├─ Metrics Ingestion                      │
│  ├─ Query APIs (for GUI)                   │
│                                            │
│  Core Services                              │
│  ├─ Device Registry                        │
│  ├─ Metrics Processor                      │
│  ├─ Alert Engine                           │
│  ├─ Online/Offline Tracker                 │
│                                            │
│  Persistence                               │
│  ├─ Users                                  │
│  ├─ Devices                                │
│  ├─ Metrics (time-series)                  │
│  ├─ Alerts                                 │
└───────────────┬────────────────────────────┘
                │ HTTPS (Push)
     ┌──────────┼───────────┐
     ▼          ▼           ▼
┌────────┐  ┌────────┐  ┌────────┐
│Agent A │  │Agent B │  │Agent C │
│Server  │  │Server  │  │Server  │
│        │  │        │  │        │
│CPU     │  │CPU     │  │CPU     │
│RAM     │  │RAM     │  │RAM     │
│Disk    │  │Disk    │  │Disk    │
│Network │  │Network │  │Network │
└────────┘  └────────┘  └────────┘

3️⃣ Layer-by-Layer Implementation Plan
🔹 Layer 1: Device Agent (Runs on EVERY server)
Responsibilities

Collect OS-level metrics

Identify device

Authenticate

Push data periodically

Internal Modules
agent/
 ├─ collector.py        # psutil metrics
 ├─ identity.py         # hostname, IP, OS
 ├─ auth.py             # token handling
 ├─ sender.py           # HTTPS push
 ├─ config.yaml         # server URL, token
 └─ main.py             # scheduler loop

Data Sent
{
  "device_id": "uuid",
  "hostname": "server-01",
  "ip": "192.168.1.10",
  "metrics": {
    "cpu": 23.5,
    "ram": 61.2,
    "disk": 54.1,
    "net_tx": 123456,
    "net_rx": 654321
  },
  "timestamp": "UTC"
}

Operational Rules

Push every N seconds

Retry on failure

Auto-start as service/daemon

🔹 Layer 2: Central Monitoring Server
Responsibilities

Trust boundary

Data aggregation

Security enforcement

Single source of truth

API Blueprint
Method	Endpoint	Purpose
POST	/auth/login	Admin login
POST	/devices/register	New agent registration
POST	/metrics	Receive metrics
GET	/devices	List all devices
GET	/devices/{id}	Device details
GET	/devices/{id}/metrics	Historical data
GET	/alerts	Active alerts
Internal Services
server/
 ├─ api/
 │   ├─ auth.py
 │   ├─ devices.py
 │   ├─ metrics.py
 │   └─ alerts.py
 ├─ services/
 │   ├─ registry.py
 │   ├─ processor.py
 │   ├─ alert_engine.py
 │   └─ heartbeat.py
 ├─ db/
 │   ├─ models.py
 │   └─ session.py
 └─ main.py

🔹 Layer 3: Database Blueprint
Tables

users

id | username | password_hash | role


devices

device_id | hostname | ip | os | last_seen | status


metrics

id | device_id | cpu | ram | disk | tx | rx | timestamp


alerts

id | device_id | metric | value | threshold | severity | timestamp

🔹 Layer 4: Admin GUI (Single Pane of Glass)
Responsibilities

Authenticate admin

Visualize all devices

Show detailed health

Surface alerts

GUI Screens
GUI/
 ├─ Login Screen
 ├─ Device List View
 │   ├─ Status (Online / Offline)
 │   ├─ CPU / RAM / Disk summary
 ├─ Device Detail View
 │   ├─ Real-time stats
 │   ├─ Charts
 ├─ Alerts View
 └─ Settings

Data Flow
GUI → Central Server → Database


🚫 GUI never talks directly to agents

4️⃣ Security Blueprint
Authentication Layers
Admin

Username/password

Hashed

Session or JWT

Device

One token per device

Token revocation supported

No OS credentials shared

Transport

HTTPS only

TLS termination at server

Optional IP allow-list

5️⃣ End-to-End Data Flow (Sequence)
1. Agent boots
2. Agent registers → gets token
3. Agent pushes metrics
4. Server stores & evaluates
5. GUI requests data
6. Server responds
7. Alerts triggered if needed

6️⃣ Deployment Blueprint
Central Server

Linux VM / bare metal

systemd service

Reverse proxy (optional)

SQLite → PostgreSQL later

Agents

Packaged executable

systemd / Windows service

Config via file or env vars

GUI

Desktop app (PySide6) OR Web

Connects only to central server

7️⃣ Build Order (Recommended)

1️⃣ Central Monitoring Server
2️⃣ Database schema
3️⃣ Device Agent
4️⃣ Admin GUI
5️⃣ Alerts & history
6️⃣ Hardening & packaging