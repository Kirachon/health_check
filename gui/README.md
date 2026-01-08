# Health Monitor GUI

React-based admin dashboard for the health monitoring system.

## Setup

```bash
cd gui
npm install

# Create environment file
cp .env.example .env

# Start development server
npm run dev
```

The GUI will be available at http://localhost:5173.

## Prerequisites

- Node.js 20.19+ or 22.12+ *(Vite 7 requirement)*

## Features

- 🔐 JWT Authentication with token refresh
- 📊 Real-time device monitoring dashboard
- 📈 Interactive metrics charts (CPU, Memory)
- 🔄 Auto-refresh every 30 seconds
- 🎨 Modern, responsive UI
- 🚀 Fast performance with Vite

## Pages

### Login (`/login`)
- Admin authentication
- Use the admin account created via `scripts/create_admin.py`

### Dashboard (`/dashboard`)
- Device list with status indicators
- Filter by online/offline
- Quick stats (total, online, offline)
- Delete devices
- Auto-refresh

### Device Detail (`/devices/:id`)
- Real-time CPU & Memory charts
- Device information panel
- Historical metrics (last hour)

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | FastAPI backend URL | `http://localhost:8001/api/v1` |
| `VITE_VM_URL` | VictoriaMetrics URL | `http://localhost:9090` |

## Troubleshooting

- Dashboard shows “Failed to fetch devices”: verify the API is running and `VITE_API_URL` points to it.
- Login redirects back to `/login`: clear `localStorage` tokens and log in again.

## Production Build

```bash
npm run build
```

Serve `dist/` behind an internal reverse proxy (Nginx/Apache). This project is intended for internal networks only.

## Tech Stack

- **React** - UI framework (see `gui/package.json` for current version)
- **TypeScript** - Type safety
- **Vite** - Build tool
- **React Router** - Routing
- **Axios** - HTTP client
- **Recharts** - Charts library

## Build for Production

```bash
npm run build
```

Output will be in `dist/` directory.
