from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import List, Optional
import secrets

from db.models import get_db, Device, User
from api.auth import get_current_user
from services.auth_service import get_password_hash


router = APIRouter(prefix="/devices", tags=["Devices"])


# Request/Response Models
class DeviceRegister(BaseModel):
    hostname: str
    ip: str
    os: Optional[str] = None


class DeviceToken(BaseModel):
    device_id: UUID
    token: str


class DeviceResponse(BaseModel):
    id: UUID
    hostname: str
    ip: str
    os: Optional[str]
    status: str
    last_seen: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class DeviceListResponse(BaseModel):
    devices: List[DeviceResponse]
    total: int


# Endpoints
@router.post("/register", response_model=DeviceToken, status_code=status.HTTP_201_CREATED)
def register_device(device_data: DeviceRegister, db: Session = Depends(get_db)):
    """Register a new device and return authentication token"""
    # Generate device token
    token = f"dev_{secrets.token_urlsafe(32)}"
    token_hash = get_password_hash(token)
    
    # Create device
    device = Device(
        hostname=device_data.hostname,
        ip=device_data.ip,
        os=device_data.os,
        token_hash=token_hash,
        status="offline"
    )
    
    db.add(device)
    db.commit()
    db.refresh(device)
    
    return DeviceToken(device_id=device.id, token=token)


@router.get("", response_model=DeviceListResponse)
def list_devices(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all registered devices (admin only)"""
    query = db.query(Device)
    
    if status:
        query = query.filter(Device.status == status)
    
    total = query.count()
    devices = query.offset(skip).limit(limit).all()
    
    return DeviceListResponse(devices=devices, total=total)


@router.get("/{device_id}", response_model=DeviceResponse)
def get_device(
    device_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get device details by ID (admin only)"""
    device = db.query(Device).filter(Device.id == device_id).first()
    
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    
    return device


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(
    device_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete device and revoke its token (admin only)"""
    device = db.query(Device).filter(Device.id == device_id).first()
    
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    
    db.delete(device)
    db.commit()


@router.post("/{device_id}/heartbeat", status_code=status.HTTP_204_NO_CONTENT)
def update_heartbeat(
    device_id: UUID,
    db: Session = Depends(get_db)
):
    """Update device last_seen timestamp (called by agents)"""
    device = db.query(Device).filter(Device.id == device_id).first()
    
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    
    device.last_seen = datetime.utcnow()
    device.status = "online"
    db.commit()
