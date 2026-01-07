from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from uuid import UUID
from typing import List, Optional
import secrets

from db.models import get_db, Device, User
from api.auth import get_current_user
from services.auth_service import get_password_hash
from config import settings


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


def _as_utc_aware(dt: datetime) -> datetime:
    """
    Normalize a datetime to UTC *aware* so arithmetic never mixes naive/aware.

    - If the DB returns naive datetimes (common with SQLite), treat them as UTC.
    - If the DB returns aware datetimes (common with Postgres), convert to UTC.
    """

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def compute_device_status(last_seen: Optional[datetime]) -> str:
    if not isinstance(last_seen, datetime):
        return "offline"

    threshold = timedelta(seconds=settings.DEVICE_OFFLINE_THRESHOLD_SECONDS)
    now_utc = datetime.now(timezone.utc)
    last_seen_utc = _as_utc_aware(last_seen)

    return "online" if (now_utc - last_seen_utc) <= threshold else "offline"


def to_device_response(device: Device) -> DeviceResponse:
    data = DeviceResponse.model_validate(device)
    # Override status based on heartbeat recency
    return DeviceResponse(
        id=data.id,
        hostname=data.hostname,
        ip=data.ip,
        os=data.os,
        status=compute_device_status(data.last_seen),
        last_seen=data.last_seen,
        created_at=data.created_at,
    )


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
        # Derive status from last_seen rather than trusting stored status.
        # Use a naive cutoff for SQL comparisons; many DB drivers (notably SQLite)
        # do not like binding timezone-aware datetimes even if the model column
        # is declared with timezone=True.
        cutoff = datetime.utcnow() - timedelta(seconds=settings.DEVICE_OFFLINE_THRESHOLD_SECONDS)
        if status == "online":
            query = query.filter(Device.last_seen.is_not(None), Device.last_seen >= cutoff)
        elif status == "offline":
            query = query.filter((Device.last_seen.is_(None)) | (Device.last_seen < cutoff))
        else:
            query = query.filter(Device.status == status)
    
    total = query.count()
    devices = query.offset(skip).limit(limit).all()

    return DeviceListResponse(devices=[to_device_response(d) for d in devices], total=total)


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
    
    return to_device_response(device)


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
