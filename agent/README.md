# Health Monitor Agent

Python-based monitoring agent that collects system metrics and sends them to the central monitoring server.

## Features

- 📊 Comprehensive metrics collection (CPU, RAM, Disk, Network)
- 🔄 OpenTelemetry OTLP protocol  
- 🔁 Automatic retry on failure
- 💓 Heartbeat for online/offline status
- 🔐 Secure device token authentication
- 🧪 Full test coverage

## Quick Start

### 1. Install Dependencies

```bash
cd agent
pip install -r requirements.txt
```

### 2. Configure Agent

Copy the template `config.yaml` to a local config file (do not commit credentials):

```bash
cp config.yaml config.local.yaml
```

Edit `config.local.yaml`:

```yaml
server_url: "http://your-vm:9090"
api_url: "http://your-api:8001"
collection_interval: 30
```

### 3. Register Device

Run once to register and get credentials:

```bash
python main.py
```

The agent will auto-register and save credentials to `config.local.yaml`.

If the server enforces registration tokens, set `registration_token` in `config.local.yaml`.

### 4. Run as Service

**Linux (systemd):**
```bash
sudo cp health-monitor-agent.service /etc/systemd/system/
sudo systemctl enable health-monitor-agent
sudo systemctl start health-monitor-agent
```

**Windows (NSSM):** use NSSM to run `agent/.venv/Scripts/python.exe agent/main.py` and point it at your `config.local.yaml`.

## Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| `server_url` | VictoriaMetrics endpoint | `http://localhost:9090` |
| `api_url` | FastAPI base URL | `http://localhost:8001` |
| `collection_interval` | Seconds between collections | `30` |
| `retry_attempts` | Max retry attempts | `3` |
| `retry_delay` | Seconds between retries | `5` |
| `registration_token` | Optional device registration token | `""` |

## Metrics Collected

### CPU
- `cpu_percent` - CPU usage percentage
- `cpu_count` - Number of CPUs
- `cpu_freq_mhz` - CPU frequency

### Memory
- `memory_percent` - RAM usage percentage
- `memory_total_gb` - Total RAM
- `memory_used_gb` - Used RAM
- `swap_percent` - Swap usage

### Disk
- `disk_percent_{mount}` - Disk usage per partition
- `disk_total_gb_{mount}` - Total disk space
- `disk_read_mb` - Cumulative read bytes
- `disk_write_mb` - Cumulative write bytes

### Network
- `network_bytes_sent` - Cumulative bytes sent
- `network_bytes_recv` - Cumulative bytes received
- `network_send_rate_mbps` - Current send rate
- `network_recv_rate_mbps` - Current receive rate

### Uptime / Storage
- `system_uptime_seconds` - Seconds since last boot
- `system_boot_time` - Boot time as Unix timestamp (seconds since epoch)
- `disk_read_bytes_mb` / `disk_write_bytes_mb` - Total disk bytes read/written since boot (MB)
- `disk_read_bytes_mb_{disk}` / `disk_write_bytes_mb_{disk}` - Per-disk bytes read/written since boot (MB)
- `disk_read_time_ms` / `disk_write_time_ms` / `disk_busy_time_ms` - Cumulative disk I/O time since boot (if available)
- `disk_read_time_ms_{disk}` / `disk_write_time_ms_{disk}` / `disk_busy_time_ms_{disk}` - Per-disk cumulative I/O time since boot (if available)

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test
pytest tests/test_collector.py -v
```

## Troubleshooting

**Agent won't start:**
- Check `server_url` is correct
- Ensure server is reachable (`ping`, `curl`)
- Check logs in `agent.log`

**Metrics not appearing:**
- Verify device is registered (`device_id` in config)
- Check device token is valid
- Review VictoriaMetrics logs

## Development

```bash
# Install dev dependencies
pip install -r requirements.txt

# Run in debug mode
LOG_LEVEL=DEBUG python main.py
```
