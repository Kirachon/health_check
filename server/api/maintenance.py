"""Maintenance window API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from db.models import get_db, MaintenanceWindow, Device, HostGroup
from api.auth import get_current_user
from services.maintenance import maintenance_service

router = APIRouter(prefix="/maintenance", tags=["Maintenance Windows"])


# Pydantic Models
class MaintenanceWindowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    recurrence: Optional[str] = Field(None, description="Cron expression for recurring windows")
    scope_type: str = Field("all", pattern="^(all|device|hostgroup)$")
    device_id: Optional[UUID] = None
    hostgroup_id: Optional[UUID] = None
    collect_data: bool = True


class MaintenanceWindowUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    recurrence: Optional[str] = None
    scope_type: Optional[str] = Field(None, pattern="^(all|device|hostgroup)$")
    device_id: Optional[UUID] = None
    hostgroup_id: Optional[UUID] = None
    collect_data: Optional[bool] = None
    active: Optional[bool] = None


class MaintenanceWindowResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    recurrence: Optional[str]
    scope_type: str
    device_id: Optional[UUID]
    hostgroup_id: Optional[UUID]
    collect_data: bool
    active: bool
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    
    # Computed fields
    is_active_now: bool = False
    scope_name: Optional[str] = None
    
    class Config:
        from_attributes = True


# Endpoints
@router.post("", response_model=MaintenanceWindowResponse, status_code=status.HTTP_201_CREATED)
def create_maintenance_window(
    window: MaintenanceWindowCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new maintenance window."""
    # Validate scope consistency
    if window.scope_type == "device" and not window.device_id:
        raise HTTPException(status_code=400, detail="device_id required when scope_type is 'device'")
    if window.scope_type == "hostgroup" and not window.hostgroup_id:
        raise HTTPException(status_code=400, detail="hostgroup_id required when scope_type is 'hostgroup'")
    if window.scope_type == "all" and (window.device_id or window.hostgroup_id):
        raise HTTPException(status_code=400, detail="device_id and hostgroup_id must be null when scope_type is 'all'")
    
    # Validate referenced entities exist
    if window.device_id:
        device = db.query(Device).filter(Device.id == window.device_id).first()
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
    if window.hostgroup_id:
        hostgroup = db.query(HostGroup).filter(HostGroup.id == window.hostgroup_id).first()
        if not hostgroup:
            raise HTTPException(status_code=404, detail="HostGroup not found")
    
    # Create window
    db_window = maintenance_service.create_window(
        db=db,
        name=window.name,
        description=window.description,
        start_time=window.start_time,
        end_time=window.end_time,
        recurrence=window.recurrence,
        scope_type=window.scope_type,
        device_id=str(window.device_id) if window.device_id else None,
        hostgroup_id=str(window.hostgroup_id) if window.hostgroup_id else None,
        collect_data=window.collect_data,
        created_by=str(current_user.id)
    )
    
    return _enrich_window_response(db_window, db)


@router.get("", response_model=List[MaintenanceWindowResponse])
def list_maintenance_windows(
    active_only: bool = Query(False, description="Filter to only currently active windows"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List all maintenance windows."""
    if active_only:
        windows = maintenance_service.get_active_windows(db)
    else:
        windows = db.query(MaintenanceWindow).order_by(MaintenanceWindow.start_time.desc()).all()
    
    return [_enrich_window_response(w, db) for w in windows]


@router.get("/active", response_model=List[MaintenanceWindowResponse])
def list_active_windows(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List currently active maintenance windows."""
    windows = maintenance_service.get_active_windows(db)
    return [_enrich_window_response(w, db) for w in windows]


@router.get("/{window_id}", response_model=MaintenanceWindowResponse)
def get_maintenance_window(
    window_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a specific maintenance window."""
    window = db.query(MaintenanceWindow).filter(MaintenanceWindow.id == window_id).first()
    if not window:
        raise HTTPException(status_code=404, detail="Maintenance window not found")
    
    return _enrich_window_response(window, db)


@router.put("/{window_id}", response_model=MaintenanceWindowResponse)
def update_maintenance_window(
    window_id: UUID,
    update: MaintenanceWindowUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update a maintenance window."""
    window = db.query(MaintenanceWindow).filter(MaintenanceWindow.id == window_id).first()
    if not window:
        raise HTTPException(status_code=404, detail="Maintenance window not found")
    
    update_data = update.model_dump(exclude_unset=True)
    
    # Validate scope consistency if updating scope
    new_scope = update_data.get("scope_type", window.scope_type)
    new_device_id = update_data.get("device_id", window.device_id)
    new_hostgroup_id = update_data.get("hostgroup_id", window.hostgroup_id)
    
    if new_scope == "device" and not new_device_id:
        raise HTTPException(status_code=400, detail="device_id required when scope_type is 'device'")
    if new_scope == "hostgroup" and not new_hostgroup_id:
        raise HTTPException(status_code=400, detail="hostgroup_id required when scope_type is 'hostgroup'")
    
    for field, value in update_data.items():
        setattr(window, field, value)
    
    db.commit()
    db.refresh(window)
    
    return _enrich_window_response(window, db)


@router.delete("/{window_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_maintenance_window(
    window_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a maintenance window."""
    window = db.query(MaintenanceWindow).filter(MaintenanceWindow.id == window_id).first()
    if not window:
        raise HTTPException(status_code=404, detail="Maintenance window not found")
    
    db.delete(window)
    db.commit()
    
    return None


@router.post("/{window_id}/deactivate", response_model=MaintenanceWindowResponse)
def deactivate_maintenance_window(
    window_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Deactivate a maintenance window (soft cancel)."""
    window = db.query(MaintenanceWindow).filter(MaintenanceWindow.id == window_id).first()
    if not window:
        raise HTTPException(status_code=404, detail="Maintenance window not found")
    
    window.active = False
    db.commit()
    db.refresh(window)
    
    return _enrich_window_response(window, db)


def _enrich_window_response(window: MaintenanceWindow, db: Session) -> MaintenanceWindowResponse:
    """Add computed fields to window response."""
    now = datetime.utcnow()
    is_active_now = (
        window.active and
        window.start_time <= now and
        window.end_time >= now
    )
    
    # Get scope name
    scope_name = None
    if window.scope_type == "device" and window.device_id:
        device = db.query(Device).filter(Device.id == window.device_id).first()
        if device:
            scope_name = device.hostname
    elif window.scope_type == "hostgroup" and window.hostgroup_id:
        hostgroup = db.query(HostGroup).filter(HostGroup.id == window.hostgroup_id).first()
        if hostgroup:
            scope_name = hostgroup.name
    elif window.scope_type == "all":
        scope_name = "All Devices"
    
    return MaintenanceWindowResponse(
        id=window.id,
        name=window.name,
        description=window.description,
        start_time=window.start_time,
        end_time=window.end_time,
        recurrence=window.recurrence,
        scope_type=window.scope_type,
        device_id=window.device_id,
        hostgroup_id=window.hostgroup_id,
        collect_data=window.collect_data,
        active=window.active,
        created_by=window.created_by,
        created_at=window.created_at,
        updated_at=window.updated_at,
        is_active_now=is_active_now,
        scope_name=scope_name
    )
