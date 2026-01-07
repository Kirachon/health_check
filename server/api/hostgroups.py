"""API endpoints for Host Group management."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import List, Optional

from db.models import get_db, HostGroup, Device, User
from api.auth import get_current_user


router = APIRouter(prefix="/hostgroups", tags=["Host Groups"])


# Request/Response Models
class HostGroupCreate(BaseModel):
    name: str
    description: Optional[str] = None


class HostGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class HostGroupResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    device_count: int
    template_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HostGroupListResponse(BaseModel):
    host_groups: List[HostGroupResponse]
    total: int


def to_hostgroup_response(hg: HostGroup) -> HostGroupResponse:
    """Convert HostGroup model to response with computed fields."""
    return HostGroupResponse(
        id=hg.id,
        name=hg.name,
        description=hg.description,
        device_count=len(hg.devices) if hg.devices else 0,
        template_count=len(hg.templates) if hg.templates else 0,
        created_at=hg.created_at,
        updated_at=hg.updated_at
    )


# Endpoints
@router.post("", response_model=HostGroupResponse, status_code=status.HTTP_201_CREATED)
def create_hostgroup(
    data: HostGroupCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new host group."""
    # Check for duplicate name
    existing = db.query(HostGroup).filter(HostGroup.name == data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Host group '{data.name}' already exists"
        )

    hg = HostGroup(name=data.name, description=data.description)
    db.add(hg)
    db.commit()
    db.refresh(hg)

    return to_hostgroup_response(hg)


@router.get("", response_model=HostGroupListResponse)
def list_hostgroups(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all host groups."""
    query = db.query(HostGroup)

    if search:
        query = query.filter(HostGroup.name.ilike(f"%{search}%"))

    total = query.count()
    hostgroups = query.order_by(HostGroup.name).offset(skip).limit(limit).all()

    return HostGroupListResponse(
        host_groups=[to_hostgroup_response(hg) for hg in hostgroups],
        total=total
    )


@router.get("/{hostgroup_id}", response_model=HostGroupResponse)
def get_hostgroup(
    hostgroup_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get host group details by ID."""
    hg = db.query(HostGroup).filter(HostGroup.id == hostgroup_id).first()

    if not hg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Host group not found")

    return to_hostgroup_response(hg)


@router.put("/{hostgroup_id}", response_model=HostGroupResponse)
def update_hostgroup(
    hostgroup_id: UUID,
    data: HostGroupUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a host group."""
    hg = db.query(HostGroup).filter(HostGroup.id == hostgroup_id).first()

    if not hg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Host group not found")

    # Check for duplicate name if changing
    if data.name and data.name != hg.name:
        existing = db.query(HostGroup).filter(HostGroup.name == data.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Host group '{data.name}' already exists"
            )
        hg.name = data.name

    if data.description is not None:
        hg.description = data.description

    db.commit()
    db.refresh(hg)

    return to_hostgroup_response(hg)


@router.delete("/{hostgroup_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_hostgroup(
    hostgroup_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a host group."""
    hg = db.query(HostGroup).filter(HostGroup.id == hostgroup_id).first()

    if not hg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Host group not found")

    db.delete(hg)
    db.commit()
