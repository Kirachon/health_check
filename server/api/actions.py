"""API endpoints for Action management (alert workflows)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import List, Optional

from db.models import get_db, Action, ActionOperation, User
from api.auth import get_current_user


router = APIRouter(prefix="/actions", tags=["Actions"])

# Valid action and operation types
VALID_ACTION_TYPES = ["notification", "remediation", "script"]
VALID_OPERATION_TYPES = ["send_email", "send_telegram", "send_slack", "run_script", "restart_service", "webhook"]


# Request/Response Models
class ActionOperationCreate(BaseModel):
    step_number: Optional[int] = 1
    operation_type: str
    parameters: Optional[str] = None  # JSON encoded parameters


class ActionOperationResponse(BaseModel):
    id: UUID
    step_number: int
    operation_type: str
    parameters: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ActionCreate(BaseModel):
    name: str
    action_type: Optional[str] = "notification"
    conditions: Optional[str] = None
    enabled: Optional[bool] = True


class ActionUpdate(BaseModel):
    name: Optional[str] = None
    action_type: Optional[str] = None
    conditions: Optional[str] = None
    enabled: Optional[bool] = None


class ActionResponse(BaseModel):
    id: UUID
    name: str
    action_type: str
    conditions: Optional[str]
    enabled: bool
    operation_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ActionDetailResponse(ActionResponse):
    operations: List[ActionOperationResponse]


class ActionListResponse(BaseModel):
    actions: List[ActionResponse]
    total: int


def get_operation_count(db: Session, action_id: UUID) -> int:
    """Get the count of operations for an action."""
    return db.query(ActionOperation).filter(ActionOperation.action_id == action_id).count()


def to_action_response(action: Action, db: Session) -> ActionResponse:
    """Convert Action model to response with computed fields."""
    return ActionResponse(
        id=action.id,
        name=action.name,
        action_type=action.action_type,
        conditions=action.conditions,
        enabled=action.enabled,
        operation_count=get_operation_count(db, action.id),
        created_at=action.created_at,
        updated_at=action.updated_at
    )


# Endpoints
@router.post("", response_model=ActionResponse, status_code=status.HTTP_201_CREATED)
def create_action(
    data: ActionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new action."""
    # Validate action type
    if data.action_type and data.action_type not in VALID_ACTION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action_type. Must be one of: {', '.join(VALID_ACTION_TYPES)}"
        )

    action = Action(
        name=data.name,
        action_type=data.action_type or "notification",
        conditions=data.conditions,
        enabled=data.enabled
    )
    db.add(action)
    db.commit()
    db.refresh(action)

    return to_action_response(action, db)


@router.get("", response_model=ActionListResponse)
def list_actions(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    action_type: Optional[str] = None,
    enabled: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all actions."""
    query = db.query(Action)

    if search:
        query = query.filter(Action.name.ilike(f"%{search}%"))
    if action_type:
        query = query.filter(Action.action_type == action_type)
    if enabled is not None:
        query = query.filter(Action.enabled == enabled)

    total = query.count()
    actions = query.order_by(Action.name).offset(skip).limit(limit).all()

    return ActionListResponse(
        actions=[to_action_response(a, db) for a in actions],
        total=total
    )


@router.get("/{action_id}", response_model=ActionDetailResponse)
def get_action(
    action_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get action details including operations."""
    action = db.query(Action).filter(Action.id == action_id).first()

    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")

    operations = db.query(ActionOperation).filter(
        ActionOperation.action_id == action_id
    ).order_by(ActionOperation.step_number).all()

    return ActionDetailResponse(
        id=action.id,
        name=action.name,
        action_type=action.action_type,
        conditions=action.conditions,
        enabled=action.enabled,
        operation_count=len(operations),
        created_at=action.created_at,
        updated_at=action.updated_at,
        operations=[ActionOperationResponse.model_validate(op) for op in operations]
    )


@router.put("/{action_id}", response_model=ActionResponse)
def update_action(
    action_id: UUID,
    data: ActionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an action."""
    action = db.query(Action).filter(Action.id == action_id).first()

    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")

    # Validate action type if provided
    if data.action_type and data.action_type not in VALID_ACTION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action_type. Must be one of: {', '.join(VALID_ACTION_TYPES)}"
        )

    if data.name is not None:
        action.name = data.name
    if data.action_type is not None:
        action.action_type = data.action_type
    if data.conditions is not None:
        action.conditions = data.conditions
    if data.enabled is not None:
        action.enabled = data.enabled

    db.commit()
    db.refresh(action)

    return to_action_response(action, db)


@router.delete("/{action_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_action(
    action_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an action and all its operations."""
    action = db.query(Action).filter(Action.id == action_id).first()

    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")

    # Delete operations first
    db.query(ActionOperation).filter(ActionOperation.action_id == action_id).delete()
    db.delete(action)
    db.commit()


# Action Operation Endpoints
@router.post("/{action_id}/operations", response_model=ActionOperationResponse, status_code=status.HTTP_201_CREATED)
def create_action_operation(
    action_id: UUID,
    data: ActionOperationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add an operation step to an action."""
    action = db.query(Action).filter(Action.id == action_id).first()

    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")

    # Validate operation type
    if data.operation_type not in VALID_OPERATION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid operation_type. Must be one of: {', '.join(VALID_OPERATION_TYPES)}"
        )

    # Auto-assign step number if not provided
    if data.step_number is None:
        max_step = db.query(ActionOperation).filter(
            ActionOperation.action_id == action_id
        ).count()
        step_number = max_step + 1
    else:
        step_number = data.step_number

    operation = ActionOperation(
        action_id=action_id,
        step_number=step_number,
        operation_type=data.operation_type,
        parameters=data.parameters
    )
    db.add(operation)
    db.commit()
    db.refresh(operation)

    return ActionOperationResponse.model_validate(operation)


@router.delete("/{action_id}/operations/{operation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_action_operation(
    action_id: UUID,
    operation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an operation from an action."""
    operation = db.query(ActionOperation).filter(
        ActionOperation.id == operation_id,
        ActionOperation.action_id == action_id
    ).first()

    if not operation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operation not found")

    db.delete(operation)
    db.commit()
