# Health Monitoring System

> Open source distributed monitoring system for servers and devices built with VictoriaMetrics, FastAPI, and React.

**Repository:** https://github.com/Kirachon/health_check

## Project Status

✅ **Production Ready** - All 5 core phases complete (83% overall)

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for agent development)
- Node.js 18+ (for GUI development)

### 1. Start Infrastructure

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

**Services:**
- VictoriaMetrics: http://localhost:9090
- Grafana: http://localhost:3001 (admin/admin)
- Alertmanager: http://localhost:9094
- PostgreSQL: localhost:5433

### 2. Verify Setup

```bash
# Check VictoriaMetrics health
curl http://localhost:9090/health

# Check PostgreSQL connection
docker exec health_monitor_db psql -U monitor_user -d health_monitor -c "SELECT version();"
```

### 3. Access Grafana

1. Navigate to http://localhost:3000
2. Login with `admin` / `admin`
3. VictoriaMetrics datasource is pre-configured

### 4. Run Backend API

```bash
cd server
python main.py
# Backend API: http://localhost:8001
```
Create an admin user via `scripts/create_admin.py` before logging in. If you are upgrading, ensure at least one admin exists (run the script if needed).

### 5. Run Frontend (Optional)

```bash
cd gui
npm install
npm run dev
# Frontend UI: http://localhost:5173
```

## 🎯 New Features (Jan 2026)

### ✅ User Management
- **CRUD API** with role-based access control (Admin, SRE, Viewer)
- **Frontend UI** for managing users, roles, and passwords
- **Security**: Self-deletion and last-admin protection

### ✅ Alerting Engine
- **Background worker** evaluating triggers every 60s
- **VictoriaMetrics integration** for metric queries
- **Threshold parsing**: `>`, `>=`, `<`, `<=`, `==`
- **Alert events** with state transitions (OK ↔ PROBLEM)
- **Acknowledge workflow** for alert management

### ✅ Agent Template Support
- **Dynamic configuration** - agents fetch metric collection config from server
- **Template system** - define metrics in templates, link to host groups
- **14 built-in collectors**: CPU, memory, disk, network, uptime, processes
- **Auto-discovery** - agents automatically collect configured metrics

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

# Frontend tests (Phase 4+)
cd gui && npm test

# Integration tests
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

## License

Apache 2.0

## Next Steps

1. ✅ Infrastructure is ready
2. → Proceed to Phase 2: Build FastAPI server
3. → Proceed to Phase 3: Build device agent
