# Health Monitor Server

FastAPI backend for the health monitoring system.

## Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env

# Start Postgres/VictoriaMetrics/Grafana via Docker first:
#   docker compose up -d

# Run server
python main.py
```

Server will be available at http://localhost:8001 (or the value of `PORT` if set)

## API Documentation

- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

## Testing

```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_auth.py -v

# Run with coverage report
pytest --cov=. --cov-report=html
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - Admin login
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - Revoke refresh token

### Devices
- `POST /api/v1/devices/register` - Register new device
- `GET /api/v1/devices` - List devices (auth required)
- `GET /api/v1/devices/{id}` - Get device details (auth required)
- `DELETE /api/v1/devices/{id}` - Delete device (auth required)
- `POST /api/v1/devices/{id}/heartbeat` - Update device status

## Admin Bootstrap

Create the first admin user via `scripts/create_admin.py` (do not ship default credentials).

Example:
```bash
python scripts/create_admin.py --username admin --password "<YOUR_STRONG_PASSWORD>" --role admin
```

## Troubleshooting

- `Errno 10048` / port bind error: port `8001` is already in use. Stop the existing process or run with `PORT=8002`.
- Login fails / UI can’t reach API: confirm `server/.env` is present and the server is listening on `http://localhost:8001`.
