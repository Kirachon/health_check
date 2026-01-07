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
