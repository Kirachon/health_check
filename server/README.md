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

# Run database migrations (PostgreSQL should be running)
# Ensure docker-compose is up: docker-compose up -d postgres

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
