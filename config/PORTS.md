## Updated Port Configuration

For security and to avoid conflicts, all services use non-standard ports:

| Service | Default Port | New Port | Access URL |
|---------|-------------|----------|------------|
| VictoriaMetrics | 8428 | **9090** | http://localhost:9090 |
| PostgreSQL | 5432 | **5433** | localhost:5433 |
| Grafana | 3000 | **3001** | http://localhost:3001 |
| Alertmanager | 9093 | **9094** | http://localhost:9094 |
| FastAPI | 8000 | **8001** | http://localhost:8001 |
| React GUI (dev) | 5173 | **5174** | http://localhost:5174 |

### Why Non-Standard Ports?

- **Security**: Less obvious to port scanners
- **Avoid Conflicts**: Common ports often already in use
- **Production Ready**: Separation from default development ports
