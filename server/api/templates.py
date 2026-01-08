"""API endpoints for Monitoring Template management."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import List, Optional

from db.models import get_db, Template, TemplateItem, User
from api.auth import get_current_user


router = APIRouter(prefix="/templates", tags=["Templates"])


# Request/Response Models
class TemplateItemCreate(BaseModel):
    name: str
    key: str
    value_type: Optional[str] = "numeric"
    units: Optional[str] = None
    update_interval: Optional[int] = 60
    enabled: Optional[bool] = True


class TemplateItemResponse(BaseModel):
    id: UUID
    name: str
    key: str
    value_type: str
    units: Optional[str]
    update_interval: int
    enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    template_type: Optional[str] = "agent"


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    template_type: Optional[str] = None


class TemplateResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    template_type: str
    item_count: int
    trigger_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TemplateDetailResponse(TemplateResponse):
    items: List[TemplateItemResponse]


class TemplateListResponse(BaseModel):
    templates: List[TemplateResponse]
    total: int


def to_template_response(t: Template) -> TemplateResponse:
    """Convert Template model to response with computed fields."""
    return TemplateResponse(
        id=t.id,
        name=t.name,
        description=t.description,
        template_type=t.template_type,
        item_count=len(t.items) if t.items else 0,
        trigger_count=len(t.triggers) if t.triggers else 0,
        created_at=t.created_at,
        updated_at=t.updated_at
    )


def to_template_detail_response(t: Template) -> TemplateDetailResponse:
    """Convert Template model to detailed response with items."""
    return TemplateDetailResponse(
        id=t.id,
        name=t.name,
        description=t.description,
        template_type=t.template_type,
        item_count=len(t.items) if t.items else 0,
        trigger_count=len(t.triggers) if t.triggers else 0,
        created_at=t.created_at,
        updated_at=t.updated_at,
        items=[TemplateItemResponse.model_validate(item) for item in t.items] if t.items else []
    )


# Template Endpoints
@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    data: TemplateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new monitoring template."""
    # Check for duplicate name
    existing = db.query(Template).filter(Template.name == data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Template '{data.name}' already exists"
        )

    template = Template(
        name=data.name,
        description=data.description,
        template_type=data.template_type
    )
    db.add(template)
    db.commit()
    db.refresh(template)

    return to_template_response(template)


@router.get("", response_model=TemplateListResponse)
def list_templates(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    template_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all monitoring templates."""
    query = db.query(Template)

    if search:
        query = query.filter(Template.name.ilike(f"%{search}%"))
    if template_type:
        query = query.filter(Template.template_type == template_type)

    total = query.count()
    templates = query.order_by(Template.name).offset(skip).limit(limit).all()

    return TemplateListResponse(
        templates=[to_template_response(t) for t in templates],
        total=total
    )


@router.get("/{template_id}", response_model=TemplateDetailResponse)
def get_template(
    template_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get template details including items."""
    template = db.query(Template).filter(Template.id == template_id).first()

    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    return to_template_detail_response(template)


@router.put("/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: UUID,
    data: TemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a template."""
    template = db.query(Template).filter(Template.id == template_id).first()

    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    # Check for duplicate name if changing
    if data.name and data.name != template.name:
        existing = db.query(Template).filter(Template.name == data.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Template '{data.name}' already exists"
            )
        template.name = data.name

    if data.description is not None:
        template.description = data.description
    if data.template_type is not None:
        template.template_type = data.template_type

    db.commit()
    db.refresh(template)

    return to_template_response(template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a template and all its items."""
    template = db.query(Template).filter(Template.id == template_id).first()

    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    db.delete(template)
    db.commit()


# Template Item Endpoints
@router.post("/{template_id}/items", response_model=TemplateItemResponse, status_code=status.HTTP_201_CREATED)
def create_template_item(
    template_id: UUID,
    data: TemplateItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add an item to a template."""
    template = db.query(Template).filter(Template.id == template_id).first()

    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    # Check for duplicate key within template
    existing = db.query(TemplateItem).filter(
        TemplateItem.template_id == template_id,
        TemplateItem.key == data.key
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Item with key '{data.key}' already exists in this template"
        )

    item = TemplateItem(
        template_id=template_id,
        name=data.name,
        key=data.key,
        value_type=data.value_type,
        units=data.units,
        update_interval=data.update_interval,
        enabled=data.enabled
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    return TemplateItemResponse.model_validate(item)


@router.delete("/{template_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template_item(
    template_id: UUID,
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an item from a template."""
    item = db.query(TemplateItem).filter(
        TemplateItem.id == item_id,
        TemplateItem.template_id == template_id
    ).first()

    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template item not found")

    db.delete(item)
    db.commit()


# Agent Configuration Endpoint - Enhanced with inheritance
class AgentConfigItemResponse(BaseModel):
    key: str
    type: str
    interval: int
    parameters: dict = {}


class AgentConfigResponse(BaseModel):
    device_id: str
    hostname: str
    templates: List[str]
    items: List[AgentConfigItemResponse]
    updated_at: str


@router.get("/agents/{device_id}/config", response_model=AgentConfigResponse)
def get_agent_config(
    device_id: UUID,
    db: Session = Depends(get_db)
):
    """Get agent configuration with full template inheritance support.
    
    Priority order:
    1. Direct device-to-template assignments (highest)
    2. Templates via host group membership
    
    Child templates override parent template items.
    """
    from db.models import Device
    from services.template_resolver import template_resolver
    
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    
    # Use template resolver for proper inheritance and priority
    config = template_resolver.get_effective_config(device, db)
    
    items = [
        AgentConfigItemResponse(
            key=item['key'],
            type=item['value_type'],
            interval=item['update_interval'],
            parameters={}
        )
        for item in config['items']
    ]
    
    return AgentConfigResponse(
        device_id=str(device_id),
        hostname=config['hostname'],
        templates=config['templates'],
        items=items,
        updated_at=datetime.utcnow().isoformat()
    )


# Bulk Device Assignment Endpoints
class BulkAssignmentRequest(BaseModel):
    device_ids: List[UUID]
    priority: Optional[int] = 0
    replace_existing: Optional[bool] = False


class BulkAssignmentResponse(BaseModel):
    assigned: int
    template_id: UUID
    device_ids: List[UUID]


@router.post("/{template_id}/assign", response_model=BulkAssignmentResponse)
def bulk_assign_devices(
    template_id: UUID,
    data: BulkAssignmentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bulk assign devices directly to a template.
    
    Direct assignments override host group assignments.
    """
    from db.models import Device
    from services.template_resolver import template_resolver
    
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    
    assigned_count = 0
    for device_id in data.device_ids:
        device = db.query(Device).filter(Device.id == device_id).first()
        if device:
            template_resolver.assign_template_to_device(
                db, str(device_id), str(template_id), data.priority
            )
            assigned_count += 1
    
    return BulkAssignmentResponse(
        assigned=assigned_count,
        template_id=template_id,
        device_ids=data.device_ids
    )


@router.delete("/{template_id}/assign")
def bulk_unassign_devices(
    template_id: UUID,
    data: BulkAssignmentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bulk remove direct device assignments from a template."""
    from services.template_resolver import template_resolver
    
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    
    for device_id in data.device_ids:
        template_resolver.unassign_template_from_device(db, str(device_id), str(template_id))
    
    return {"message": f"Unassigned {len(data.device_ids)} devices from template"}


class DeviceAssignmentResponse(BaseModel):
    device_id: UUID
    hostname: str
    priority: int
    assigned_at: datetime


@router.get("/{template_id}/devices", response_model=List[DeviceAssignmentResponse])
def list_assigned_devices(
    template_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all devices directly assigned to a template."""
    from db.models import Device, device_template
    
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    
    # Query assignments with device info
    assignments = db.execute(
        device_template.select().where(device_template.c.template_id == template_id)
    ).fetchall()
    
    result = []
    for assignment in assignments:
        device = db.query(Device).filter(Device.id == assignment.device_id).first()
        if device:
            result.append(DeviceAssignmentResponse(
                device_id=device.id,
                hostname=device.hostname,
                priority=assignment.priority,
                assigned_at=assignment.assigned_at
            ))
    
    return result


# Template Inheritance Endpoints
class SetParentRequest(BaseModel):
    parent_template_id: Optional[UUID] = None


@router.put("/{template_id}/parent", response_model=TemplateResponse)
def set_parent_template(
    template_id: UUID,
    data: SetParentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Set or remove the parent template for inheritance."""
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    
    if data.parent_template_id:
        # Validate parent exists
        parent = db.query(Template).filter(Template.id == data.parent_template_id).first()
        if not parent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent template not found")
        
        # Prevent circular reference
        if data.parent_template_id == template_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Template cannot be its own parent")
        
        # Check for deeper circular references
        from services.template_resolver import template_resolver
        current = parent
        while current.parent_template:
            if current.parent_template.id == template_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Circular inheritance detected"
                )
            current = current.parent_template
        
        template.parent_template_id = data.parent_template_id
    else:
        template.parent_template_id = None
    
    db.commit()
    db.refresh(template)
    
    return to_template_response(template)


class InheritanceChainResponse(BaseModel):
    templates: List[TemplateResponse]
    effective_item_count: int


@router.get("/{template_id}/inheritance", response_model=InheritanceChainResponse)
def get_inheritance_chain(
    template_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the full inheritance chain for a template."""
    from services.template_resolver import template_resolver
    
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    
    try:
        chain = template_resolver.resolve_template_chain(template, db)
        merged_items = template_resolver.merge_template_items(chain)
        
        return InheritanceChainResponse(
            templates=[to_template_response(t) for t in chain],
            effective_item_count=len(merged_items)
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{template_id}/propagate")
def propagate_config(
    template_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Force config propagation to all devices using this template.
    
    This triggers agents to refresh their configuration.
    """
    from db.models import Device, device_template
    
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    
    # Count affected devices (direct + via hostgroups)
    affected_devices = set()
    
    # Direct assignments
    direct = db.execute(
        device_template.select().where(device_template.c.template_id == template_id)
    ).fetchall()
    affected_devices.update(str(a.device_id) for a in direct)
    
    # Via host groups
    for hostgroup in template.host_groups:
        for device in hostgroup.devices:
            affected_devices.add(str(device.id))
    
    # Touch template updated_at to signal config change
    template.updated_at = datetime.utcnow()
    db.commit()
    
    return {
        "message": f"Config propagation triggered for {len(affected_devices)} devices",
        "affected_devices": len(affected_devices),
        "template": template.name
    }


