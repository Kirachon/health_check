# Manual Testing Guide

## ✅ Prerequisites

- Backend running: `cd server && python main.py` → http://localhost:8001
- Frontend running: `cd gui && npm run dev` → http://localhost:5173
- Database migrated: `python -c "from db.models import Base, engine; Base.metadata.create_all(bind=engine)"`

---

## 🧪 Test Plan

### 1️⃣ User Management (5 min)

**Access:** http://localhost:5173 → Login → "User Management" in sidebar

**Test Cases:**

| # | Action | Expected Result |
|---|--------|----------------|
| 1.1 | Click "Add User" | Modal opens with username/password/role fields |
| 1.2 | Create user: `test_user`, pw: `test123456`, role: `viewer` | User appears in table |
| 1.3 | Click edit icon → Change role to `sre` | Role badge updates to "SRE" |
| 1.4 | Click key icon → Reset password to `newpass123` | Success message |
| 1.5 | Click delete icon → Confirm | User removed from table |
| 1.6 | Try deleting `admin` user | Error: "Cannot delete yourself" |

**API Test:**
```bash
python test_new_features.py
# Should show: ✓ User CRUD operations successful
```

---

### 2️⃣ Templates & Agent Config (10 min)

**Access:** http://localhost:5173 → "Templates" in sidebar

**Test Cases:**

| # | Action | Expected Result |
|---|--------|----------------|
| 2.1 | Create template: "OS Monitoring" | Template created |
| 2.2 | Add items: `system.cpu.percent`, `system.memory.percent` (60s interval) | 2 items added |
| 2.3 | Go to "Host Groups" → Create group: "Production Servers" | Group created |
| 2.4 | Link template "OS Monitoring" to group | Template badge appears |
| 2.5 | Add a device to the group | Device shows in group |

**API Test:**
```bash
# Get device ID from UI or:
curl http://localhost:8001/api/v1/devices -H "Authorization: Bearer <token>" | jq .

# Test agent config endpoint:
curl http://localhost:8001/api/v1/templates/agents/<device-id>/config
# Should return: {"device_id": "...", "items": [{"key": "system.cpu.percent", ...}]}
```

---

### 3️⃣ Alerting Engine (15 min)

**Prerequisites:**
- VictoriaMetrics running: `docker-compose up -d victoria` (port 9090)
- Backend logs showing: "Starting background alerting worker..."

**Test Cases:**

| # | Action | Expected Result |
|---|--------|----------------|
| 3.1 | Go to "Triggers" → Create trigger: `cpu_percent > 80`, severity: `high` | Trigger created |
| 3.2 | Enable trigger | Status: "Enabled" |
| 3.3 | Wait 60s, check backend logs | Log: "Evaluating trigger..." |
| 3.4 | Check alerts API: `GET /api/v1/alerts` | Alert events listed (if trigger fired) |
| 3.5 | Click "Acknowledge" on an alert | Status changes to "Acknowledged" |

**Backend Logs to Monitor:**
```
INFO:     Starting background alerting worker...
INFO:     Trigger <name> state changed: OK -> PROBLEM
```

**API Test:**
```bash
# Alert summary
curl http://localhost:8001/api/v1/alerts/summary/counts -H "Authorization: Bearer <token>"
# Returns: {"total": X, "problem": Y, "ok": Z, "unacknowledged": W}
```

---

## 🐛 Common Issues & Fixes

### Issue: "AlertEvent table not found"
**Fix:**
```bash
cd server
python -c "from db.models import Base, engine; Base.metadata.create_all(bind=engine)"
```

### Issue: Alerting worker not running
**Check:** Backend logs should show "Starting background alerting worker..."
**Fix:** Restart backend: `cd server && python main.py`

### Issue: No alerts generated
**Check:**
1. VictoriaMetrics running? `curl http://localhost:9090/api/v1/query?query=cpu_percent`
2. Trigger enabled? Check UI or DB
3. Threshold met? Check metric values in VictoriaMetrics

### Issue: Agent config returns empty items
**Cause:** Device not linked to host group with templates
**Fix:** Create host group → link template → add device to group

---

## ✅ Success Criteria

- [ ] Can create/edit/delete users
- [ ] Can create templates with items
- [ ] Can link templates to host groups
- [ ] Agent config endpoint returns items
- [ ] Alerting worker runs without errors
- [ ] Alert events created when triggers fire
- [ ] Can acknowledge alerts

---

## 📊 Quick Verification Script

```bash
# Run automated tests
python test_new_features.py

# Expected output:
# ✅ Authentication successful!
# ✓ User Management: Working
# ✓ Alerting API: Working  
# ✓ Agent Config: Working
```
