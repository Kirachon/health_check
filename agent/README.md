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

Edit `config.yaml`:

```yaml
server_url: "http://your-server:8428"
collection_interval: 30
```

### 3. Register Device

Run once to register and get credentials:

```bash
python main.py
```

The agent will auto-register and save credentials to `config.yaml`.

### 4. Run as Service

**Linux (systemd):**
```bash
sudo cp health-monitor-agent.service /etc/systemd/system/
sudo systemctl enable health-monitor-agent
sudo systemctl start health-monitor-agent
```

**Windows:**
```bash
# Run as administrator
python main.py install
python main.py start
```

## Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| `server_url` | VictoriaMetrics endpoint | `http://localhost:8428` |
| `collection_interval` | Seconds between collections | `30` |
| `retry_attempts` | Max retry attempts | `3` |
| `retry_delay` | Seconds between retries | `5` |

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
