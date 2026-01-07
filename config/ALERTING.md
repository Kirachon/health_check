# Alerting Configuration Guide

This document explains how to configure alerting for the Health Monitor system.

## Alert Rules

Alert rules are defined in `config/grafana/provisioning/alerting/rules.yml`.

### Configured Alerts

| Alert | Threshold | Duration | Severity |
|-------|-----------|----------|----------|
| Critical CPU Usage | CPU > 90% | 5 minutes | Critical |
| High CPU Usage | CPU > 80% | 5 minutes | Warning |
| Critical Memory Usage | Memory > 85% | 5 minutes | Critical |
| Critical Disk Usage | Disk > 90% | 2 minutes | Critical |
| Device Offline | No metrics | 2 minutes | Warning |

## Notification Channels

### 1. Email Notifications

Edit `config/grafana/provisioning/alerting/contactpoints.yml`:

```yaml
- name: email-notifications
  receivers:
    - type: email
      settings:
        addresses: your-email@example.com  # Change this
        singleEmail: false
```

**SMTP Configuration** (in Grafana):
- Go to Grafana → Configuration → Settings
- Configure SMTP server settings
- Or via environment variables in docker-compose.yml:
  ```yaml
  environment:
    GF_SMTP_ENABLED: "true"
    GF_SMTP_HOST: "smtp.gmail.com:587"
    GF_SMTP_USER: "your-email@gmail.com"
    GF_SMTP_PASSWORD: "your-app-password"
    GF_SMTP_FROM_ADDRESS: "grafana@example.com"
  ```

### 2. Slack Notifications

1. Create Slack Incoming Webhook:
   - Go to https://api.slack.com/apps
   - Create new app → Incoming Webhooks
   - Add webhook to workspace
   - Copy webhook URL

2. Update `contactpoints.yml`:
   ```yaml
   - name: slack-notifications
     receivers:
       - type: slack
         settings:
           url: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
           recipient: '#monitoring'  # Your channel
   ```

### 3. Webhook (API Integration)

Alerts are sent to FastAPI backend at `/api/v1/alerts/webhook`.

To implement the webhook endpoint, add to `server/api/alerts.py`:

```python
from fastapi import APIRouter

router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.post("/webhook")
async def alert_webhook(payload: dict):
    # Process alert, store in database, send notifications
    print(f"Received alert: {payload}")
    return {"status": "received"}
```

## Alert Routing

### Critical Alerts
- Sent to: Email + Slack + Webhook
- Repeat interval: 1 hour
- Applies to: CPU > 90%, Memory > 85%, Disk > 90%

### Warning Alerts
- Sent to: Slack + Webhook
- Repeat interval: 4 hours
- Applies to: CPU > 80%, Device Offline

## Testing Alerts

### 1. Test CPU Alert

```bash
# Stress test CPU on monitored device
stress --cpu 8 --timeout 60s
```

### 2. Test Memory Alert

```python
# Python script to consume memory
import numpy as np
data = [np.zeros((1000, 1000)) for _ in range(100)]
```

### 3. Test Device Offline

```bash
# Stop the agent
sudo systemctl stop health-monitor-agent

# Wait 2+ minutes, alert should fire
```

### 4. Manual Test via Grafana

1. Go to Grafana → Alerting → Alert rules
2. Click on an alert rule
3. Click "Test" button
4. Verify notification delivery

## Customizing Alerts

### Change Thresholds

Edit `rules.yml` and modify the `params` value:

```yaml
- evaluator:
    params:
      - 90  # Change this threshold
    type: gt
```

### Add New Alert

```yaml
- uid: new_alert_id
  title: New Alert Name
  condition: C
  data:
    - refId: A
      model:
        expr: metric_name  # VictoriaMetrics query
  for: 5m  # Duration
  annotations:
    description: 'Description here'
  labels:
    severity: critical  # or warning
```

### Modify Check Frequency

In `rules.yml`, change the `interval`:

```yaml
groups:
  - name: device_health_alerts
    interval: 1m  # Check every 1 minute
```

## Alertmanager Integration

For advanced routing with Alertmanager, alerts are also sent there via Grafana's Alertmanager integration.

Edit `config/alertmanager/alertmanager.yml` for custom routing rules.

## Troubleshooting

**Alerts not firing:**
- Check Grafana logs: `docker logs health_monitor_grafana`
- Verify datasource connection
- Test alert rule manually in Grafana UI

**Notifications not received:**
- Verify contact point configuration
- Check notification channel logs
- Test notification delivery in Grafana

**False positives:**
- Increase `for` duration in alert rules
- Adjust thresholds based on baseline metrics
- Add inhibition rules to suppress during maintenance
