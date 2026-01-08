"""API endpoints for Network Map Visualization."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
from uuid import UUID
from typing import List, Optional, Dict, Any
import json

from db.models import (
    get_db, NetworkMap, MapElement, MapLink,
    Device, HostGroup, User
)
from api.auth import get_current_user

router = APIRouter(prefix="/maps", tags=["Network Maps"])


# Pydantic Models
class MapElementCreate(BaseModel):
    element_type: str = "device"  # device, hostgroup, label, shape
    device_id: Optional[UUID] = None
    hostgroup_id: Optional[UUID] = None
    label: Optional[str] = None
    icon: Optional[str] = None
    x: int
    y: int
    data: Optional[Dict[str, Any]] = None

class MapLinkCreate(BaseModel):
    source_element_id: UUID
    target_element_id: UUID
    link_type: str = "network"
    color: Optional[str] = "#666666"
    width: Optional[int] = 2
    label: Optional[str] = None

class NetworkMapCreate(BaseModel):
    name: str
    description: Optional[str] = None
    width: Optional[int] = 1920
    height: Optional[int] = 1080
    background_image: Optional[str] = None

class MapElementUpdate(BaseModel):
    x: Optional[int] = None
    y: Optional[int] = None
    label: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

class MapElementResponse(BaseModel):
    id: UUID
    map_id: UUID
    element_type: str
    device_id: Optional[UUID]
    hostgroup_id: Optional[UUID]
    label: Optional[str]
    icon: Optional[str]
    x: int
    y: int
    width: int
    height: int
    data: Optional[str]
    
    # Resolved names
    device_name: Optional[str] = None
    hostgroup_name: Optional[str] = None

    class Config:
        from_attributes = True

class MapLinkResponse(BaseModel):
    id: UUID
    map_id: UUID
    source_element_id: UUID
    target_element_id: UUID
    link_type: str
    color: str
    width: int
    label: Optional[str]

    class Config:
        from_attributes = True

class NetworkMapResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    width: int
    height: int
    background_image: Optional[str]
    created_at: datetime
    updated_at: datetime
    elements: List[MapElementResponse] = []
    links: List[MapLinkResponse] = []

    class Config:
        from_attributes = True


# Endpoints
@router.post("", response_model=NetworkMapResponse, status_code=status.HTTP_201_CREATED)
def create_map(
    data: NetworkMapCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new network map."""
    network_map = NetworkMap(
        name=data.name,
        description=data.description,
        width=data.width,
        height=data.height,
        background_image=data.background_image,
        created_by=current_user.id
    )
    db.add(network_map)
    db.commit()
    db.refresh(network_map)
    return network_map


@router.get("", response_model=List[NetworkMapResponse])
def list_maps(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all network maps."""
    maps = db.query(NetworkMap).all()
    # Don't load full details for list view (optimization)
    return maps


@router.get("/{map_id}", response_model=NetworkMapResponse)
def get_map(
    map_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get full map details with elements and links."""
    network_map = db.query(NetworkMap).filter(NetworkMap.id == map_id).first()
    if not network_map:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Map not found")
    
    # Enroll names
    response = NetworkMapResponse.from_orm(network_map)
    
    # Process elements to add resolved names
    for element in response.elements:
        if element.device_id:
            device = db.query(Device).filter(Device.id == element.device_id).first()
            if device:
                element.device_name = device.hostname
        if element.hostgroup_id:
            hg = db.query(HostGroup).filter(HostGroup.id == element.hostgroup_id).first()
            if hg:
                element.hostgroup_name = hg.name
                
    return response


@router.put("/{map_id}", response_model=NetworkMapResponse)
def update_map(
    map_id: UUID,
    data: NetworkMapCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update map metadata."""
    network_map = db.query(NetworkMap).filter(NetworkMap.id == map_id).first()
    if not network_map:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Map not found")
    
    network_map.name = data.name
    network_map.description = data.description
    network_map.width = data.width
    network_map.height = data.height
    network_map.background_image = data.background_image
    
    db.commit()
    db.refresh(network_map)
    return network_map


@router.delete("/{map_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_map(
    map_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a map."""
    network_map = db.query(NetworkMap).filter(NetworkMap.id == map_id).first()
    if not network_map:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Map not found")
    
    db.delete(network_map)
    db.commit()


# Element Management
@router.post("/{map_id}/elements", response_model=MapElementResponse)
def add_element(
    map_id: UUID,
    data: MapElementCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add an element to the map."""
    network_map = db.query(NetworkMap).filter(NetworkMap.id == map_id).first()
    if not network_map:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Map not found")
    
    element = MapElement(
        map_id=map_id,
        element_type=data.element_type,
        device_id=data.device_id,
        hostgroup_id=data.hostgroup_id,
        label=data.label,
        icon=data.icon,
        x=data.x,
        y=data.y,
        data=json.dumps(data.data) if data.data else None
    )
    db.add(element)
    db.commit()
    db.refresh(element)
    
    # Determine label if not provided
    response = MapElementResponse.from_orm(element)
    if not response.label:
        if element.device_id:
            device = db.query(Device).filter(Device.id == element.device_id).first()
            if device:
                response.device_name = device.hostname
                response.label = device.hostname
        elif element.hostgroup_id:
            hg = db.query(HostGroup).filter(HostGroup.id == element.hostgroup_id).first()
            if hg:
                response.hostgroup_name = hg.name
                response.label = hg.name
                
    return response


@router.put("/{map_id}/elements/{element_id}", response_model=MapElementResponse)
def update_element(
    map_id: UUID,
    element_id: UUID,
    data: MapElementUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update element position or properties."""
    element = db.query(MapElement).filter(
        MapElement.id == element_id,
        MapElement.map_id == map_id
    ).first()
    
    if not element:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Element not found")
    
    if data.x is not None:
        element.x = data.x
    if data.y is not None:
        element.y = data.y
    if data.label is not None:
        element.label = data.label
    if data.data is not None:
        current_data = json.loads(element.data) if element.data else {}
        current_data.update(data.data)
        element.data = json.dumps(current_data)
        
    db.commit()
    db.refresh(element)
    return element


@router.delete("/{map_id}/elements/{element_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_element(
    map_id: UUID,
    element_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an element."""
    element = db.query(MapElement).filter(
        MapElement.id == element_id,
        MapElement.map_id == map_id
    ).first()
    
    if not element:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Element not found")
    
    db.delete(element)
    db.commit()


# Link Management
@router.post("/{map_id}/links", response_model=MapLinkResponse)
def add_link(
    map_id: UUID,
    data: MapLinkCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Connect two map elements."""
    # Validate elements exist in this map
    source = db.query(MapElement).filter(MapElement.id == data.source_element_id, MapElement.map_id == map_id).first()
    target = db.query(MapElement).filter(MapElement.id == data.target_element_id, MapElement.map_id == map_id).first()
    
    if not source or not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source or target element not found in this map")
    
    link = MapLink(
        map_id=map_id,
        source_element_id=data.source_element_id,
        target_element_id=data.target_element_id,
        link_type=data.link_type,
        color=data.color,
        width=data.width,
        label=data.label
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


@router.delete("/{map_id}/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_link(
    map_id: UUID,
    link_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a link."""
    link = db.query(MapLink).filter(
        MapLink.id == link_id,
        MapLink.map_id == map_id
    ).first()
    
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")
    
    db.delete(link)
    db.commit()


@router.get("/{map_id}/status")
def get_map_status(
    map_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get real-time status for all elements in a map."""
    elements = db.query(MapElement).filter(MapElement.map_id == map_id).all()
    
    status_map = {}
    for element in elements:
        if element.device_id:
            device = db.query(Device).filter(Device.id == element.device_id).first()
            if device:
                # Determine status based on device state
                # Use last_seen recency to avoid placeholder latency values
                last_seen = device.last_seen
                last_seen_age_seconds = None
                if last_seen:
                    now_utc = datetime.utcnow()
                    delta = now_utc - last_seen if last_seen.tzinfo is None else now_utc - last_seen.replace(tzinfo=None)
                    last_seen_age_seconds = int(delta.total_seconds())
                status_map[str(element.id)] = {
                    "status": "online" if device.status == "online" else "offline",
                    "last_seen": device.last_seen.isoformat() if device.last_seen else None,
                    "last_seen_age_seconds": last_seen_age_seconds
                }
        else:
             status_map[str(element.id)] = {"status": "ok"}
             
    return status_map
