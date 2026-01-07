# Health Monitoring System

> Open source distributed monitoring system for servers and devices built with VictoriaMetrics, FastAPI, and React.

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
- VictoriaMetrics: http://localhost:8428
- Grafana: http://localhost:3000 (admin/admin)
- Alertmanager: http://localhost:9093
- PostgreSQL: localhost:5432

### 2. Verify Setup

```bash
# Check VictoriaMetrics health
curl http://localhost:8428/health

# Check PostgreSQL connection
docker exec health_monitor_db psql -U monitor_user -d health_monitor -c "SELECT version();"
```

### 3. Access Grafana

1. Navigate to http://localhost:3000
2. Login with `admin` / `admin`
3. VictoriaMetrics datasource is pre-configured

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
| Alerting | Alertmanager | Latest |
| Frontend | React + Vite | 18 |
| Agent | Python + psutil | 3.11+ |

## Development Phases

- [x] Phase 1: Infrastructure Setup
- [ ] Phase 2: Central Server (FastAPI)
- [ ] Phase 3: Device Agent
- [ ] Phase 4: Admin GUI
- [ ] Phase 5: Alerting & Notifications
- [ ] Phase 6: Deployment & Packaging

## Testing

```bash
# Backend tests (Phase 2+)
cd server && pytest tests/ -v

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
