# Alerting Configuration Guide

This document explains how to configure alerting for the Health Monitor system.
This deployment is intended for internal server/department networks only and should not use external/cloud endpoints.

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
        addresses: internal-alerts@example.local  # Change this
        singleEmail: false
```

**SMTP Configuration** (in Grafana):
- Go to Grafana → Configuration → Settings
- Configure SMTP server settings
- Or via environment variables in docker-compose.yml:
  ```yaml
  environment:
    GF_SMTP_ENABLED: "true"
    GF_SMTP_HOST: "internal-smtp:587"
    GF_SMTP_USER: "internal-user"
    GF_SMTP_PASSWORD: "internal-password"
    GF_SMTP_FROM_ADDRESS: "alerts@example.local"
```
### 2. Webhook (API Integration)

Alerts are sent to the FastAPI backend at `http://localhost:8001/api/v1/alerts/webhook`.

This endpoint is implemented and expects a webhook token by default. You can pass the token either:
- As a query param: `?token=YOUR_TOKEN`
- Or via header: `X-Webhook-Token: YOUR_TOKEN`

Update `contactpoints.yml` to include the token:

```yaml
- name: webhook-api
  receivers:
    - type: webhook
      settings:
        url: http://localhost:8001/api/v1/alerts/webhook?token=${ALERT_WEBHOOK_TOKEN}
        httpMethod: POST
```

Set the token for Grafana (docker-compose example):

```yaml
environment:
  ALERT_WEBHOOK_TOKEN: "<YOUR_RANDOM_TOKEN>"
```

## Alert Routing

### Critical Alerts
- Sent to: Email + Webhook
- Repeat interval: 1 hour
- Applies to: CPU > 90%, Memory > 85%, Disk > 90%

### Warning Alerts
- Sent to: Webhook
- Repeat interval: 4 hours
- Applies to: CPU > 80%, Device Offline

## Alert Retention

Alert events are retained for 30 days by default.

Manual cleanup:

```bash
python scripts/cleanup_alerts.py --days 30
```

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

**Grafana restarting in a loop:**
- Check `docker logs --tail 200 health_monitor_grafana`
- Common cause: invalid alert rule provisioning YAML (for provisioned rules, each rule group must set a `folder`).

**Notifications not received:**
- Verify contact point configuration
- Check notification channel logs
- Test notification delivery in Grafana

**False positives:**
- Increase `for` duration in alert rules
- Adjust thresholds based on baseline metrics
- Add inhibition rules to suppress during maintenance
