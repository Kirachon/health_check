"""API endpoints for Trigger/Alert Rule management."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import List, Optional

from db.models import get_db, Trigger, Template, User
from api.auth import get_current_user


router = APIRouter(prefix="/triggers", tags=["Triggers"])

# Valid severity levels (Zabbix-style)
VALID_SEVERITIES = ["disaster", "high", "average", "warning", "info"]


# Request/Response Models
class TriggerCreate(BaseModel):
    name: str
    expression: str
    severity: Optional[str] = "average"
    description: Optional[str] = None
    template_id: Optional[UUID] = None
    enabled: Optional[bool] = True


class TriggerUpdate(BaseModel):
    name: Optional[str] = None
    expression: Optional[str] = None
    severity: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None


class TriggerResponse(BaseModel):
    id: UUID
    name: str
    expression: str
    severity: str
    description: Optional[str]
    enabled: bool
    template_id: Optional[UUID]
    template_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TriggerListResponse(BaseModel):
    triggers: List[TriggerResponse]
    total: int


def to_trigger_response(t: Trigger) -> TriggerResponse:
    """Convert Trigger model to response."""
    return TriggerResponse(
        id=t.id,
        name=t.name,
        expression=t.expression,
        severity=t.severity,
        description=t.description,
        enabled=t.enabled,
        template_id=t.template_id,
        template_name=t.template.name if t.template else None,
        created_at=t.created_at,
        updated_at=t.updated_at
    )


# Endpoints
@router.post("", response_model=TriggerResponse, status_code=status.HTTP_201_CREATED)
def create_trigger(
    data: TriggerCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new trigger."""
    # Validate severity
    if data.severity and data.severity not in VALID_SEVERITIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid severity. Must be one of: {', '.join(VALID_SEVERITIES)}"
        )

    # Validate template_id if provided
    if data.template_id:
        template = db.query(Template).filter(Template.id == data.template_id).first()
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )

    trigger = Trigger(
        name=data.name,
        expression=data.expression,
        severity=data.severity or "average",
        description=data.description,
        template_id=data.template_id,
        enabled=data.enabled
    )
    db.add(trigger)
    db.commit()
    db.refresh(trigger)

    return to_trigger_response(trigger)


@router.get("", response_model=TriggerListResponse)
def list_triggers(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    severity: Optional[str] = None,
    enabled: Optional[bool] = None,
    template_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all triggers."""
    query = db.query(Trigger)

    if search:
        query = query.filter(Trigger.name.ilike(f"%{search}%"))
    if severity:
        query = query.filter(Trigger.severity == severity)
    if enabled is not None:
        query = query.filter(Trigger.enabled == enabled)
    if template_id:
        query = query.filter(Trigger.template_id == template_id)

    total = query.count()
    triggers = query.order_by(Trigger.name).offset(skip).limit(limit).all()

    return TriggerListResponse(
        triggers=[to_trigger_response(t) for t in triggers],
        total=total
    )


@router.get("/{trigger_id}", response_model=TriggerResponse)
def get_trigger(
    trigger_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get trigger details by ID."""
    trigger = db.query(Trigger).filter(Trigger.id == trigger_id).first()

    if not trigger:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trigger not found")

    return to_trigger_response(trigger)


@router.put("/{trigger_id}", response_model=TriggerResponse)
def update_trigger(
    trigger_id: UUID,
    data: TriggerUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a trigger."""
    trigger = db.query(Trigger).filter(Trigger.id == trigger_id).first()

    if not trigger:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trigger not found")

    # Validate severity if provided
    if data.severity and data.severity not in VALID_SEVERITIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid severity. Must be one of: {', '.join(VALID_SEVERITIES)}"
        )

    if data.name is not None:
        trigger.name = data.name
    if data.expression is not None:
        trigger.expression = data.expression
    if data.severity is not None:
        trigger.severity = data.severity
    if data.description is not None:
        trigger.description = data.description
    if data.enabled is not None:
        trigger.enabled = data.enabled

    db.commit()
    db.refresh(trigger)

    return to_trigger_response(trigger)


@router.delete("/{trigger_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trigger(
    trigger_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a trigger."""
    trigger = db.query(Trigger).filter(Trigger.id == trigger_id).first()

    if not trigger:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trigger not found")

    db.delete(trigger)
    db.commit()


@router.post("/{trigger_id}/toggle", response_model=TriggerResponse)
def toggle_trigger(
    trigger_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toggle trigger enabled/disabled status."""
    trigger = db.query(Trigger).filter(Trigger.id == trigger_id).first()

    if not trigger:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trigger not found")

    trigger.enabled = not trigger.enabled
    db.commit()
    db.refresh(trigger)

    return to_trigger_response(trigger)
