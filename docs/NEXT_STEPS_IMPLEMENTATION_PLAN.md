# Implementation Plan: Remaining Next Steps

> **Purpose**: Comprehensive guide for implementing 4 remaining features to complete the Zabbix-grade monitoring system.
> 
> **Target Agent**: This document is designed for handoff to another AI agent for implementation.

---

## Project Context

### Codebase Structure
```
d:\GitProjects\health_check\
├── server/                    # FastAPI backend
│   ├── api/                   # API routers (auth.py, devices.py, hostgroups.py, templates.py, triggers.py, actions.py)
│   ├── db/                    # Database models + get_db (models.py)
│   ├── services/              # Business logic (auth_service.py, etc.)
│   ├── workers/               # Background workers (optional future)
│   ├── tests/                 # pytest tests
│   └── main.py                # FastAPI app entry
├── gui/                       # React + Vite frontend
│   ├── src/api/client.ts      # API client with auth
│   ├── src/pages/             # Page components
│   └── src/context/           # Auth context
├── agent/                     # Python metrics collector
│   ├── collector.py           # Metrics collection
│   ├── sender.py              # OTLP sender
│   └── main.py                # Agent entry
└── docker-compose.yml         # VictoriaMetrics, PostgreSQL, Grafana
```

### Existing Patterns to Follow

**Backend API Pattern** (see `server/api/hostgroups.py`):
- FastAPI router with prefix
- Pydantic models for request/response
- SQLAlchemy queries with `get_db` dependency
- `get_current_user` for auth
- HTTPException for errors
- snake_case for API fields

**Compatibility notes (current codebase reality):**
- Password hashing uses `bcrypt` directly via `server/services/auth_service.py` (not `passlib`).
- Tables are created via `Base.metadata.create_all(...)` in `server/main.py` (no Alembic config checked in).
- Tests run against SQLite (`server/tests/conftest.py`), so schema changes must remain SQLite-compatible.

**Frontend Page Pattern** (see `gui/src/pages/HostGroups.tsx`):
- `useState` + `useEffect` + `useCallback` for data
- Debounced search with 300ms delay
- Modal pattern for create/edit/delete
- Loading spinner, empty state, error banner
- glassmorphism styling with inline `<style>` tag

**Test Pattern** (see `server/tests/test_hostgroups.py`):
- pytest fixtures in `conftest.py`
- `authenticated_client` fixture provides JWT
- Test CRUD, auth, validation, edge cases

### Compatibility Review (as of 2026-01-07)
- This plan originally referenced non-existent modules (`db.database`) and Alembic migrations; the current server uses `db.models` + `Base.metadata.create_all(...)`.
- Password hashing in the server is `bcrypt` via `server/services/auth_service.py` (so any new endpoints should reuse `get_password_hash` instead of introducing `passlib`).
- SQLite is used for tests, so Postgres-only types/DDL should be avoided in new features unless guarded.
- Security note (future work): `agent/collector.py` executes `user_parameters` commands with `shell=True`; treat `agent/config.yaml` as trusted-only, or add allowlisting/sandboxing before production use.

---

## Overview

| Step | Feature | Complexity | Est. Time | Dependencies |
|------|---------|------------|-----------|--------------|
| 1 | User CRUD API | Medium | 2-3 hrs | None |
| 2 | Wire UserManagement.tsx | Low | 1-2 hrs | Step 1 |
| 3 | Alerting Engine | High | 4-6 hrs | Triggers, Actions APIs |
| 4 | Agent Template Support | High | 4-6 hrs | Templates API |

---

## Step 1: User CRUD API

### Goal
Create a backend API for user management with role-based access control (RBAC). Only admins can manage users.

### 1.1 Database Model Update
**File**: `server/db/models.py`

**Current reality (already implemented):**
- `User` currently has: `id`, `username`, `password_hash`, `role`, `created_at`, `updated_at` (see `server/db/models.py`).
- There is **no** Alembic config in-repo; schema changes should be handled via:
  - Manual SQL for Postgres (local/dev), or
  - Recreating dev volumes, and
  - Tests recreate SQLite tables via `create_all/drop_all`.

**Choose a path before implementing User CRUD:**

**Option A (recommended / highest compatibility):** implement User CRUD on existing columns only.
- Manage: `username`, `role`, password reset (update `password_hash`).
- Skip: `email`, `status`, `last_login` for now.

**Option B (more Zabbix-like):** extend the User model.
- Add columns: `email`, `status` (`active|suspended`), `last_login`.
- Add Python deps if you use `EmailStr`: `email-validator` (not currently listed in `server/requirements.txt`).
- Update Docker init + test fixtures (`config/postgres/init.sql`, `server/tests/conftest.py`).

### 1.2 Create Users API
**File**: `server/api/users.py` (NEW)

```python
"""User management API - Admin only."""
from typing import Optional, List, Literal
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db.models import get_db, User
from api.auth import get_current_user
from services.auth_service import get_password_hash

router = APIRouter(prefix="/users", tags=["Users"])
Role = Literal["admin", "sre", "viewer"]


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=255, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=8)
    role: Role = "viewer"


class UserUpdate(BaseModel):
    role: Optional[Role] = None


class PasswordReset(BaseModel):
    password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    id: UUID
    username: str
    role: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int
    limit: int
    offset: int


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


@router.get("", response_model=UserListResponse)
def list_users(
    search: Optional[str] = None,
    role: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    query = db.query(User)
    if search:
        query = query.filter(User.username.ilike(f"%{search}%"))
    if role:
        query = query.filter(User.role == role)

    total = query.count()
    users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    return UserListResponse(users=[UserResponse.model_validate(u) for u in users], total=total, limit=limit, offset=offset)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse.model_validate(user)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    user = User(username=data.username, password_hash=get_password_hash(data.password), role=data.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    data: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if data.role and data.role != "admin" and str(user.id) == str(admin.id):
        admin_count = db.query(User).filter(User.role == "admin").count()
        if admin_count <= 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot demote the last admin")

    if data.role is not None:
        user.role = data.role

    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    user_id: UUID,
    data: PasswordReset,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if str(user_id) == str(admin.id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Use profile/password flow for self reset")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.password_hash = get_password_hash(data.password)
    db.commit()


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if str(user_id) == str(admin.id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.role == "admin":
        admin_count = db.query(User).filter(User.role == "admin").count()
        if admin_count <= 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete the last admin")

    db.delete(user)
    db.commit()

# Option B: add email/status/last_login fields + suspend endpoint once schema is extended
```

### 1.3 Register Router
**File**: `server/main.py`

```python
from api import users  # Add import

# Register under API_V1_PREFIX (consistent with other routers)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
```

### 1.4 Tests
**File**: `server/tests/test_users.py` (NEW)

```python
"""Tests for User CRUD API (Option A-compatible)."""
from fastapi.testclient import TestClient


class TestUserCRUD:
    def test_list_users_requires_auth(self, client: TestClient):
        response = client.get("/api/v1/users")
        assert response.status_code in (401, 403)  # missing auth header

    def test_list_users_as_admin(self, authenticated_client: TestClient):
        response = authenticated_client.get("/api/v1/users")
        assert response.status_code == 200

    def test_create_user(self, authenticated_client: TestClient):
        response = authenticated_client.post(
            "/api/v1/users",
            json={"username": "newuser", "password": "testpass123", "role": "viewer"},
        )
        assert response.status_code == 201
        assert response.json()["username"] == "newuser"
```

### 1.5 Implementation Tasks (Step 1)
- [ ] Decide Option A vs Option B (schema changes) and update this plan accordingly
- [ ] Create `server/api/users.py` endpoints (admin-only): list/get/create/update/delete/reset-password
- [ ] Register router in `server/main.py` under `settings.API_V1_PREFIX`
- [ ] Add tests `server/tests/test_users.py` following existing pytest patterns
- [ ] Run: `cd server && venv\\Scripts\\python -m pytest -q`

Note: `server/tests/conftest.py` already provides an `authenticated_client` fixture for admin-authenticated requests.

---

## Step 2: Wire UserManagement.tsx

### Goal
Replace mock data with live API calls following the established pattern.

### 2.1 Extend API Client
**File**: `gui/src/api/client.ts`

Add to `APIClient` class:
```typescript
// ============ USERS API ============
async listUsers(params?: { search?: string; role?: string; status?: string; limit?: number; offset?: number }) {
    return this.authRequest<{
        users: Array<{
            id: string;
            username: string;
            email: string;
            role: 'admin' | 'sre' | 'viewer';
            status: 'active' | 'suspended';
            created_at: string;
            last_login: string | null;
        }>;
        total: number;
    }>('get', '/users', { params });
}

async createUser(data: { username: string; email: string; password: string; role?: string }) {
    return this.authRequest<UserResponse>('post', '/users', { data });
}

async updateUser(id: string, data: { email?: string; role?: string; status?: string }) {
    return this.authRequest<UserResponse>('put', `/users/${id}`, { data });
}

async deleteUser(id: string) {
    return this.authRequest<void>('delete', `/users/${id}`);
}

async toggleUserSuspend(id: string) {
    return this.authRequest<UserResponse>('post', `/users/${id}/suspend`);
}
```

### 2.2 Update Component
**File**: `gui/src/pages/UserManagement.tsx`

Replace the entire file with live API integration. Key changes:
1. Remove `mockUsers` array
2. Add state: `users`, `loading`, `error`, `showModal`, `editingUser`, `formData`, `deleteId`
3. Add `fetchUsers` with `useCallback` + debounced search
4. Add create/edit modal (same pattern as HostGroups)
5. Add delete confirmation modal
6. Add suspend toggle button
7. Add role filter dropdown

See `HostGroups.tsx` for exact pattern - replicate that structure.

### 2.3 Add Role Guard in App.tsx (Optional)
```tsx
// Only show UserManagement for admins
{currentUser?.role === 'admin' && (
    <Route path="/users" element={<UserManagement />} />
)}
```

---

## Step 3: Alerting Engine

### Goal
Background service that evaluates triggers and executes actions.

### 3.1 Database Models
**File**: `server/db/models.py`

Add:
```python
class AlertEvent(Base):
    """Records when a trigger fires or recovers."""
    __tablename__ = "alert_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trigger_id = Column(UUID(as_uuid=True), ForeignKey("triggers.id", ondelete="CASCADE"), nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), nullable=False)  # PROBLEM, OK
    previous_status = Column(String(20), nullable=True)
    value = Column(Float, nullable=True)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    trigger = relationship("Trigger", back_populates="alert_events")
    executions = relationship("ActionExecution", back_populates="alert_event", cascade="all, delete-orphan")

class ActionExecution(Base):
    """Records action execution attempts."""
    __tablename__ = "action_executions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_id = Column(UUID(as_uuid=True), ForeignKey("actions.id", ondelete="CASCADE"), nullable=False)
    alert_event_id = Column(UUID(as_uuid=True), ForeignKey("alert_events.id", ondelete="CASCADE"), nullable=False)
    operation_type = Column(String(50), nullable=False)  # email, webhook, script
    status = Column(String(20), nullable=False)  # pending, success, failed
    output = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    action = relationship("Action")
    alert_event = relationship("AlertEvent", back_populates="executions")

# Add to Trigger model:
# alert_events = relationship("AlertEvent", back_populates="trigger", cascade="all, delete-orphan")
```

### 3.2 Trigger Evaluator Service
**File**: `server/services/alerting.py` (NEW)

```python
"""Trigger evaluation engine."""
import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime
import httpx
from sqlalchemy.orm import Session

from db.models import Trigger, AlertEvent, Action
from db.models import SessionLocal

logger = logging.getLogger(__name__)

class TriggerEvaluator:
    def __init__(self, vm_url: str):
        self.vm_url = vm_url
        self.trigger_states: Dict[str, str] = {}  # {trigger_id: "OK"|"PROBLEM"}
    
    async def evaluate_all(self):
        """Evaluate all enabled triggers."""
        db = SessionLocal()
        try:
            triggers = db.query(Trigger).filter(Trigger.enabled == True).all()
            logger.info(f"Evaluating {len(triggers)} triggers")
            
            for trigger in triggers:
                try:
                    await self.evaluate_trigger(db, trigger)
                except Exception as e:
                    logger.error(f"Error evaluating trigger {trigger.id}: {e}")
            
            db.commit()
        finally:
            db.close()
    
    async def evaluate_trigger(self, db: Session, trigger: Trigger):
        """Evaluate a single trigger against VictoriaMetrics."""
        # Query VictoriaMetrics
        value = await self.query_vm(trigger.expression)
        
        # Determine state (simplified: non-None means PROBLEM)
        # Real implementation should parse expression for threshold
        new_state = "PROBLEM" if value is not None and value > 0 else "OK"
        old_state = self.trigger_states.get(str(trigger.id), "OK")
        
        # State changed?
        if new_state != old_state:
            self.trigger_states[str(trigger.id)] = new_state
            
            # Create alert event
            event = AlertEvent(
                trigger_id=trigger.id,
                status=new_state,
                previous_status=old_state,
                value=value,
                message=f"Trigger '{trigger.name}' changed from {old_state} to {new_state}"
            )
            db.add(event)
            db.flush()  # Get event ID
            
            logger.info(f"Alert state change: {trigger.name} -> {new_state}")
            
            # Execute actions if PROBLEM
            if new_state == "PROBLEM":
                await self.execute_actions(db, trigger, event)
    
    async def query_vm(self, expression: str) -> Optional[float]:
        """Query VictoriaMetrics for expression result."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.vm_url}/api/v1/query",
                    params={"query": expression}
                )
                data = resp.json()
                
                if data.get("status") == "success":
                    result = data.get("data", {}).get("result", [])
                    if result and len(result) > 0:
                        return float(result[0]["value"][1])
        except Exception as e:
            logger.warning(f"VM query failed for '{expression}': {e}")
        return None
    
    async def execute_actions(self, db: Session, trigger: Trigger, event: AlertEvent):
        """Find and execute matching actions."""
        from services.action_executor import ActionExecutor
        
        # Find actions that match trigger severity
        actions = db.query(Action).filter(Action.enabled == True).all()
        executor = ActionExecutor(db)
        
        for action in actions:
            # Check conditions (simplified: match severity)
            if action.conditions:
                import json
                conditions = json.loads(action.conditions) if isinstance(action.conditions, str) else action.conditions
                if "severity" in conditions:
                    if trigger.severity not in conditions["severity"]:
                        continue
            
            await executor.execute(action, event)
```

### 3.3 Action Executor Service
**File**: `server/services/action_executor.py` (NEW)

```python
"""Action execution service."""
import asyncio
import logging
import json
import subprocess
from datetime import datetime
from typing import Optional
import httpx
from sqlalchemy.orm import Session

from db.models import Action, ActionOperation, ActionExecution, AlertEvent

logger = logging.getLogger(__name__)

class ActionExecutor:
    def __init__(self, db: Session):
        self.db = db
    
    async def execute(self, action: Action, event: AlertEvent):
        """Execute all operations for an action."""
        # Get operations (would need ActionOperation model)
        # For now, execute based on action_type
        
        execution = ActionExecution(
            action_id=action.id,
            alert_event_id=event.id,
            operation_type=action.action_type,
            status="pending"
        )
        self.db.add(execution)
        self.db.flush()
        
        try:
            if action.action_type == "notification":
                await self.send_notification(action, event)
            elif action.action_type == "webhook":
                await self.send_webhook(action, event)
            elif action.action_type == "script":
                await self.run_script(action, event)
            
            execution.status = "success"
            execution.completed_at = datetime.utcnow()
            logger.info(f"Action {action.name} executed successfully")
            
        except Exception as e:
            execution.status = "failed"
            execution.error = str(e)
            execution.completed_at = datetime.utcnow()
            logger.error(f"Action {action.name} failed: {e}")
    
    async def send_notification(self, action: Action, event: AlertEvent):
        """Send email/SMS notification."""
        # TODO: Implement email sending via SMTP or SendGrid
        logger.info(f"Would send notification for event {event.id}")
    
    async def send_webhook(self, action: Action, event: AlertEvent):
        """Send webhook POST request."""
        conditions = json.loads(action.conditions) if action.conditions else {}
        url = conditions.get("webhook_url")
        
        if not url:
            raise ValueError("No webhook_url in action conditions")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(url, json={
                "event_id": str(event.id),
                "trigger_id": str(event.trigger_id),
                "status": event.status,
                "message": event.message,
                "value": event.value,
                "timestamp": event.created_at.isoformat()
            })
    
    async def run_script(self, action: Action, event: AlertEvent):
        """Execute local script."""
        conditions = json.loads(action.conditions) if action.conditions else {}
        script = conditions.get("script_path")
        
        if not script:
            raise ValueError("No script_path in action conditions")
        
        # Run script with event data as env vars
        env = {
            "ALERT_EVENT_ID": str(event.id),
            "ALERT_STATUS": event.status,
            "ALERT_MESSAGE": event.message or "",
            "ALERT_VALUE": str(event.value) if event.value else ""
        }
        
        result = subprocess.run(
            [script],
            capture_output=True,
            text=True,
            timeout=60,
            env=env
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Script failed: {result.stderr}")
```

### 3.4 Background Worker
**File**: `server/workers/alerting_worker.py` (NEW)

```python
"""Background alerting worker."""
import asyncio
import logging
import os

from services.alerting import TriggerEvaluator

logger = logging.getLogger(__name__)

async def alerting_loop():
    """Main alerting evaluation loop."""
    vm_url = os.getenv("VM_URL", "http://localhost:8428")
    interval = int(os.getenv("ALERTING_INTERVAL", "60"))
    
    evaluator = TriggerEvaluator(vm_url)
    logger.info(f"Starting alerting worker (interval={interval}s)")
    
    while True:
        try:
            await evaluator.evaluate_all()
        except Exception as e:
            logger.error(f"Alerting loop error: {e}")
        
        await asyncio.sleep(interval)

def start_alerting_worker():
    """Start the alerting worker in background task."""
    import asyncio
    loop = asyncio.get_event_loop()
    loop.create_task(alerting_loop())
```

### 3.5 Start Worker on App Startup
**File**: `server/main.py`

```python
from workers.alerting_worker import start_alerting_worker

@app.on_event("startup")
async def startup_event():
    """Start background workers."""
    start_alerting_worker()
```

### 3.6 Alert Events API
**File**: `server/api/alerts.py` (NEW)

```python
"""Alert events API."""
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.models import get_db
from db.models import AlertEvent, ActionExecution, User
from api.auth import get_current_user

router = APIRouter()

class AlertEventResponse(BaseModel):
    id: str
    trigger_id: str
    status: str
    previous_status: Optional[str]
    value: Optional[float]
    message: Optional[str]
    created_at: datetime

class AlertEventListResponse(BaseModel):
    events: List[AlertEventResponse]
    total: int

@router.get("/events", response_model=AlertEventListResponse)
def list_alert_events(
    trigger_id: Optional[UUID] = None,
    status: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user)
):
    """List alert events."""
    query = db.query(AlertEvent)
    
    if trigger_id:
        query = query.filter(AlertEvent.trigger_id == trigger_id)
    if status:
        query = query.filter(AlertEvent.status == status)
    
    total = query.count()
    events = query.order_by(AlertEvent.created_at.desc()).offset(offset).limit(limit).all()
    
    return AlertEventListResponse(
        events=[AlertEventResponse(
            id=str(e.id),
            trigger_id=str(e.trigger_id),
            status=e.status,
            previous_status=e.previous_status,
            value=e.value,
            message=e.message,
            created_at=e.created_at
        ) for e in events],
        total=total
    )

# Register in main.py:
# app.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
```

---

## Step 4: Agent Template Support

### Goal
Agent dynamically fetches its collection configuration from the server.

### 4.1 Server Endpoint for Agent Config
**File**: `server/api/templates.py`

Add endpoint:
```python
@router.get("/agents/{device_id}/config")
def get_agent_config(
    device_id: UUID,
    db: Session = Depends(get_db)
):
    """Get agent configuration based on linked templates."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Get templates via host groups
    items = []
    seen_keys = set()
    
    for host_group in device.host_groups:
        # Would need template-hostgroup relationship
        # For now, get all templates
        templates = db.query(Template).all()
        
        for template in templates:
            for item in template.items:
                if item.item_key not in seen_keys:
                    seen_keys.add(item.item_key)
                    items.append({
                        "key": item.item_key,
                        "type": item.item_type,
                        "interval": item.interval or 60,
                        "parameters": item.parameters or {}
                    })
    
    return {
        "device_id": str(device_id),
        "items": items,
        "updated_at": datetime.utcnow().isoformat()
    }
```

### 4.2 Agent Config Sync
**File**: `agent/config_sync.py` (NEW)

```python
"""Template configuration sync from server."""
import asyncio
import logging
from typing import Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

class ConfigSync:
    def __init__(self, server_url: str, device_id: str, token: str):
        self.server_url = server_url.rstrip('/')
        self.device_id = device_id
        self.token = token
        self.config: Dict = {"items": []}
        self._last_updated: Optional[str] = None
    
    async def fetch_config(self) -> bool:
        """Fetch configuration from server. Returns True if changed."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"Authorization": f"Bearer {self.token}"}
                resp = await client.get(
                    f"{self.server_url}/templates/agents/{self.device_id}/config",
                    headers=headers
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("updated_at") != self._last_updated:
                        self.config = data
                        self._last_updated = data.get("updated_at")
                        logger.info(f"Config updated: {len(data.get('items', []))} items")
                        return True
                else:
                    logger.warning(f"Config fetch failed: {resp.status_code}")
        except Exception as e:
            logger.error(f"Config sync error: {e}")
        return False
    
    async def sync_loop(self, interval: int = 300):
        """Continuously sync config from server."""
        while True:
            await self.fetch_config()
            await asyncio.sleep(interval)
    
    def get_items(self) -> List[Dict]:
        """Get current item configuration."""
        return self.config.get("items", [])
```

### 4.3 Dynamic Collector
**File**: `agent/dynamic_collector.py` (NEW)

```python
"""Template-based dynamic metrics collector."""
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
import psutil
import subprocess

from config_sync import ConfigSync

logger = logging.getLogger(__name__)

class Metric:
    def __init__(self, name: str, value: float, labels: Dict[str, str] = None):
        self.name = name
        self.value = value
        self.labels = labels or {}
        self.timestamp = time.time()

class DynamicCollector:
    def __init__(self, config_sync: ConfigSync):
        self.config_sync = config_sync
        self.collectors = {
            "system.cpu.percent": self._collect_cpu_percent,
            "system.memory.percent": self._collect_memory_percent,
            "system.disk.percent": self._collect_disk_percent,
            "system.uptime": self._collect_uptime,
            "custom.script": self._collect_script,
        }
    
    async def collect_all(self) -> List[Metric]:
        """Collect all configured metrics."""
        metrics = []
        items = self.config_sync.get_items()
        
        for item in items:
            try:
                metric = await self.collect_item(item)
                if metric:
                    metrics.append(metric)
            except Exception as e:
                logger.error(f"Failed to collect {item.get('key')}: {e}")
        
        return metrics
    
    async def collect_item(self, item: Dict) -> Optional[Metric]:
        """Collect a single item based on type."""
        item_type = item.get("type", "")
        collector = self.collectors.get(item_type)
        
        if collector:
            value = await collector(item.get("parameters", {}))
            if value is not None:
                return Metric(name=item.get("key", item_type), value=value)
        else:
            logger.warning(f"Unknown item type: {item_type}")
        return None
    
    # ============ COLLECTORS ============
    
    async def _collect_cpu_percent(self, params: Dict) -> float:
        return psutil.cpu_percent(interval=1)
    
    async def _collect_memory_percent(self, params: Dict) -> float:
        return psutil.virtual_memory().percent
    
    async def _collect_disk_percent(self, params: Dict) -> float:
        path = params.get("path", "/")
        return psutil.disk_usage(path).percent
    
    async def _collect_uptime(self, params: Dict) -> float:
        return time.time() - psutil.boot_time()
    
    async def _collect_script(self, params: Dict) -> Optional[float]:
        script = params.get("script")
        if not script:
            return None
        
        try:
            result = subprocess.run(
                script,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            return float(result.stdout.strip())
        except Exception as e:
            logger.error(f"Script failed: {e}")
            return None
```

### 4.4 LLD Discovery
**File**: `agent/discovery.py` (NEW)

```python
"""Low-Level Discovery for dynamic resources."""
import psutil
from typing import List, Dict

class LLDDiscovery:
    """Discover dynamic resources for template item prototypes."""
    
    def discover_filesystems(self) -> List[Dict[str, str]]:
        """Discover mounted filesystems."""
        result = []
        for partition in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                result.append({
                    "{#FSNAME}": partition.mountpoint,
                    "{#FSTYPE}": partition.fstype,
                    "{#DEVICE}": partition.device,
                    "{#FSTOTAL}": str(usage.total),
                })
            except PermissionError:
                continue
        return result
    
    def discover_network_interfaces(self) -> List[Dict[str, str]]:
        """Discover network interfaces."""
        result = []
        stats = psutil.net_if_stats()
        addrs = psutil.net_if_addrs()
        
        for iface, st in stats.items():
            if st.isup:
                addr_list = addrs.get(iface, [])
                ip = next((a.address for a in addr_list if a.family.name == 'AF_INET'), "")
                result.append({
                    "{#IFNAME}": iface,
                    "{#IFADDR}": ip,
                    "{#IFSPEED}": str(st.speed),
                })
        return result
    
    def discover_processes(self, name_filter: str = None) -> List[Dict[str, str]]:
        """Discover running processes."""
        result = []
        for proc in psutil.process_iter(['pid', 'name', 'username']):
            try:
                info = proc.info
                if name_filter and name_filter not in info['name']:
                    continue
                result.append({
                    "{#PID}": str(info['pid']),
                    "{#PROCNAME}": info['name'],
                    "{#PROCUSER}": info['username'] or "",
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return result
```

### 4.5 Update Agent Main
**File**: `agent/main.py`

```python
"""Agent main entry point with template support."""
import asyncio
import os
import logging

from config_sync import ConfigSync
from dynamic_collector import DynamicCollector
from sender import MetricsSender

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    # Configuration
    server_url = os.getenv("SERVER_URL", "http://localhost:8000")
    device_id = os.getenv("DEVICE_ID")
    token = os.getenv("AUTH_TOKEN")
    otlp_endpoint = os.getenv("OTLP_ENDPOINT", "http://localhost:4318")
    
    if not device_id or not token:
        logger.error("DEVICE_ID and AUTH_TOKEN required")
        return
    
    # Initialize components
    config_sync = ConfigSync(server_url, device_id, token)
    collector = DynamicCollector(config_sync)
    sender = MetricsSender(otlp_endpoint, device_id)
    
    # Initial config fetch
    await config_sync.fetch_config()
    
    # Start config sync in background
    asyncio.create_task(config_sync.sync_loop(interval=300))
    
    # Main collection loop
    logger.info("Agent started")
    while True:
        try:
            metrics = await collector.collect_all()
            if metrics:
                await sender.send(metrics)
                logger.debug(f"Sent {len(metrics)} metrics")
        except Exception as e:
            logger.error(f"Collection error: {e}")
        
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Verification Checklist

### Step 1: User CRUD API
- [ ] `server/api/users.py` created with all endpoints
- [ ] Router registered in `main.py`
- [ ] `POST /users` creates user with hashed password
- [ ] `GET /users` returns paginated list
- [ ] `PUT /users/{id}` updates fields
- [ ] `DELETE /users/{id}` removes user
- [ ] Non-admin gets 403 on all endpoints
- [ ] Cannot delete self or demote last admin
- [ ] Tests pass: `pytest server/tests/test_users.py -v`

### Step 2: UserManagement.tsx
- [ ] API client methods added
- [ ] Users load from API on mount
- [ ] Search filters users (debounced)
- [ ] Create modal submits to API
- [ ] Edit modal pre-fills and updates
- [ ] Delete shows confirmation
- [ ] Suspend toggles status
- [ ] Frontend builds: `npm run build`

### Step 3: Alerting Engine
- [ ] `AlertEvent` and `ActionExecution` models added
- [ ] Migration created and run
- [ ] `server/services/alerting.py` created
- [ ] `server/services/action_executor.py` created
- [ ] Background worker starts on app startup
- [ ] Triggers evaluated every 60s
- [ ] State changes create `AlertEvent` records
- [ ] Actions executed on state change
- [ ] `/alerts/events` returns history
- [ ] Integration test with test trigger

### Step 4: Agent Template Support
- [ ] `/templates/agents/{device_id}/config` endpoint added
- [ ] `agent/config_sync.py` created
- [ ] `agent/dynamic_collector.py` created
- [ ] `agent/discovery.py` created
- [ ] Agent fetches config on startup
- [ ] Agent refreshes config every 5 minutes
- [ ] Dynamic collector uses fetched items
- [ ] LLD discovers filesystems and interfaces
- [ ] Agent tests pass

---

## File Summary

| New Files | Location | Purpose |
|-----------|----------|---------|
| `users.py` | `server/api/` | User CRUD API |
| `test_users.py` | `server/tests/` | User API tests |
| `alerting.py` | `server/services/` | Trigger evaluator |
| `action_executor.py` | `server/services/` | Action runner |
| `alerting_worker.py` | `server/workers/` | Background loop |
| `alerts.py` | `server/api/` | Alert history API |
| `config_sync.py` | `agent/` | Template sync |
| `dynamic_collector.py` | `agent/` | Template-based collection |
| `discovery.py` | `agent/` | LLD discovery |

| Modified Files | Changes |
|----------------|---------|
| `server/db/models.py` | Add AlertEvent, ActionExecution, update User |
| `server/main.py` | Register routers, start worker |
| `server/api/templates.py` | Add agent config endpoint |
| `server/tests/conftest.py` | Add admin_client fixture |
| `gui/src/api/client.ts` | Add user API methods |
| `gui/src/pages/UserManagement.tsx` | Replace mock with live API |
| `agent/main.py` | Integrate template support |
