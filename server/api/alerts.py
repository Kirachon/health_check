"""Alert Events API endpoints."""
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from uuid import UUID
import secrets
from fastapi import APIRouter, Depends, HTTPException, Query, status, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import settings
from db.models import get_db, AlertEvent, Trigger, User, Device
from api.auth import get_current_user
from schemas.alerts import GrafanaWebhookPayload

router = APIRouter(prefix="/alerts", tags=["Alerts"])


class AlertEventResponse(BaseModel):
    id: UUID
    trigger_id: UUID
    trigger_name: Optional[str] = None
    device_id: Optional[UUID] = None
    status: str
    value: Optional[float] = None
    message: Optional[str] = None
    acknowledged: bool
    acknowledged_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AlertEventListResponse(BaseModel):
    events: List[AlertEventResponse]
    total: int
    limit: int
    offset: int


class AcknowledgeRequest(BaseModel):
    message: Optional[str] = None


def to_response(event: AlertEvent) -> AlertEventResponse:
    """Convert AlertEvent to response model with trigger name."""
    return AlertEventResponse(
        id=event.id,
        trigger_id=event.trigger_id,
        trigger_name=event.trigger.name if event.trigger else None,
        device_id=event.device_id,
        status=event.status,
        value=float(event.value) if event.value else None,
        message=event.message,
        acknowledged=event.acknowledged,
        acknowledged_at=event.acknowledged_at,
        created_at=event.created_at
    )


def _normalize_status(raw_status: str) -> str:
    value = (raw_status or "").strip().lower()
    if value in {"firing", "alerting", "triggered", "problem"}:
        return "PROBLEM"
    if value in {"resolved", "ok", "normal"}:
        return "OK"
    return raw_status.upper() if raw_status else "PROBLEM"


def _find_device_by_labels(db: Session, labels: Dict[str, str]) -> Optional[Device]:
    for key in ("host_name", "hostname", "host", "instance", "device"):
        hostname = labels.get(key)
        if hostname:
            return db.query(Device).filter(Device.hostname == hostname).first()
    return None


def _sanitize_text(value: str, max_len: int) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ").replace("\t", " ")
    text = " ".join(text.split())
    return text[:max_len]


def _sanitize_map(data: Dict[str, str], max_len: int) -> Dict[str, str]:
    safe: Dict[str, str] = {}
    for key, val in (data or {}).items():
        if key and val is not None:
            safe[str(key)] = _sanitize_text(val, max_len)
    return safe


def _build_message(labels: Dict[str, str], annotations: Dict[str, str]) -> str:
    safe_labels = _sanitize_map(labels, 200)
    safe_annotations = _sanitize_map(annotations, 500)
    summary = safe_annotations.get("summary")
    description = safe_annotations.get("description")
    parts = []
    if summary:
        parts.append(summary)
    if description and description != summary:
        parts.append(description)
    if not parts:
        parts.append("Grafana alert received.")
    if safe_labels.get("alertname"):
        parts.append(f"Alert: {safe_labels.get('alertname')}")
    if safe_labels.get("severity"):
        parts.append(f"Severity: {safe_labels.get('severity')}")
    return "\n".join(parts)


def _cleanup_old_alert_events(db: Session, retention_days: int) -> int:
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    deleted = (
        db.query(AlertEvent)
        .filter(AlertEvent.created_at < cutoff)
        .delete(synchronize_session=False)
    )
    db.commit()
    return deleted


@router.get("", response_model=AlertEventListResponse)
def list_alerts(
    status: Optional[str] = None,
    trigger_id: Optional[UUID] = None,
    acknowledged: Optional[bool] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """List alert events with optional filters."""
    query = db.query(AlertEvent)
    
    if status:
        query = query.filter(AlertEvent.status == status)
    if trigger_id:
        query = query.filter(AlertEvent.trigger_id == trigger_id)
    if acknowledged is not None:
        query = query.filter(AlertEvent.acknowledged == acknowledged)
    
    total = query.count()
    events = query.order_by(AlertEvent.created_at.desc()).offset(offset).limit(limit).all()
    
    return AlertEventListResponse(
        events=[to_response(e) for e in events],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/{alert_id}", response_model=AlertEventResponse)
def get_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Get a specific alert event."""
    event = db.query(AlertEvent).filter(AlertEvent.id == alert_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return to_response(event)


@router.post("/{alert_id}/acknowledge", response_model=AlertEventResponse)
def acknowledge_alert(
    alert_id: UUID,
    data: AcknowledgeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Acknowledge an alert event."""
    event = db.query(AlertEvent).filter(AlertEvent.id == alert_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    
    if event.acknowledged:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Alert already acknowledged")
    
    event.acknowledged = True
    event.acknowledged_at = datetime.utcnow()
    event.acknowledged_by = current_user.id
    if data.message:
        event.message = f"{event.message or ''}\n\nAcknowledged: {data.message}"
    
    db.commit()
    db.refresh(event)
    return to_response(event)


@router.get("/summary/counts")
def get_alert_counts(
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Get summary counts of alerts."""
    total = db.query(AlertEvent).count()
    problem = db.query(AlertEvent).filter(AlertEvent.status == "PROBLEM").count()
    unacknowledged = db.query(AlertEvent).filter(AlertEvent.acknowledged == False).count()
    
    return {
        "total": total,
        "problem": problem,
        "ok": total - problem,
        "unacknowledged": unacknowledged
    }


@router.post("/webhook", status_code=status.HTTP_202_ACCEPTED)
def alert_webhook(
    payload: GrafanaWebhookPayload,
    db: Session = Depends(get_db),
    token: Optional[str] = Query(default=None),
    x_webhook_token: Optional[str] = Header(default=None, alias="X-Webhook-Token"),
):
    """Receive Grafana webhook alerts and store as AlertEvent rows."""
    if settings.ALERT_WEBHOOK_REQUIRE_TOKEN:
        expected = settings.ALERT_WEBHOOK_TOKEN
        if not expected:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Webhook token not configured",
            )
        provided = x_webhook_token or token
        if not provided or not secrets.compare_digest(str(provided), str(expected)):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook token",
            )

    if not payload.alerts:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No alerts in payload")

    trigger_cache: Dict[str, Trigger] = {}
    created_count = 0

    for alert in payload.alerts:
        labels = alert.labels or {}
        annotations = alert.annotations or {}
        alert_name = labels.get("alertname") or "Grafana Alert"
        severity = (labels.get("severity") or "warning").lower()
        description = annotations.get("summary") or annotations.get("description")

        trigger = trigger_cache.get(alert_name)
        if not trigger:
            trigger = db.query(Trigger).filter(Trigger.name == alert_name).first()
            if not trigger:
                trigger = Trigger(
                    name=alert_name,
                    expression="external:grafana",
                    severity=severity,
                    description=description,
                    enabled=True,
                )
                db.add(trigger)
                db.flush()
            trigger_cache[alert_name] = trigger

        device = _find_device_by_labels(db, labels)
        event = AlertEvent(
            trigger_id=trigger.id,
            device_id=device.id if device else None,
            status=_normalize_status(alert.status),
            value=None,
            message=_build_message(labels, annotations),
        )
        db.add(event)
        created_count += 1

    db.commit()
    return {"received": created_count}


@router.post("/cleanup")
def cleanup_alerts(
    retention_days: Optional[int] = Query(default=None, ge=1, le=3650),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete old alert events (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    days = retention_days or settings.ALERT_EVENT_RETENTION_DAYS
    deleted = _cleanup_old_alert_events(db, days)
    return {"deleted": deleted, "retention_days": days}
