"""API endpoints for Remote Command Execution."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import List, Optional
import json
import re

from db.models import (
    get_db, CommandTemplate, CommandExecution, RemediationRule, 
    Device, Trigger, User
)
from api.auth import get_current_user

router = APIRouter(prefix="/commands", tags=["Commands"])


# Pydantic Models
class ParameterSchema(BaseModel):
    name: str
    type: str = "string"  # string, int, bool
    required: bool = False
    default: Optional[str] = None


class CommandTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    command: str
    command_type: Optional[str] = "shell"
    requires_approval: Optional[bool] = True
    allowed_roles: Optional[str] = "admin"
    max_execution_time: Optional[int] = 300
    parameters: Optional[List[ParameterSchema]] = None
    allowed_hostgroups: Optional[str] = None


class CommandTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    command: Optional[str] = None
    requires_approval: Optional[bool] = None
    max_execution_time: Optional[int] = None
    parameters: Optional[List[ParameterSchema]] = None


class CommandTemplateResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    command: str
    command_type: str
    requires_approval: bool
    allowed_roles: str
    max_execution_time: int
    parameters: Optional[str]
    allowed_hostgroups: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ExecuteCommandRequest(BaseModel):
    device_id: UUID
    template_id: Optional[UUID] = None
    command: Optional[str] = None  # Direct command if no template
    parameters: Optional[dict] = None


class CommandExecutionResponse(BaseModel):
    id: UUID
    device_id: UUID
    device_hostname: Optional[str] = None
    template_id: Optional[UUID]
    template_name: Optional[str] = None
    command: str
    parameters: Optional[str]
    status: str
    queued_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    exit_code: Optional[int]
    stdout: Optional[str]
    stderr: Optional[str]
    source: str
    requested_by: Optional[UUID]

    class Config:
        from_attributes = True


class RemediationRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_id: UUID
    command_template_id: UUID
    enabled: Optional[bool] = True
    auto_approve: Optional[bool] = False
    max_executions_per_hour: Optional[int] = 3
    cooldown_minutes: Optional[int] = 15


class RemediationRuleResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    trigger_id: UUID
    trigger_name: Optional[str] = None
    command_template_id: UUID
    command_template_name: Optional[str] = None
    enabled: bool
    auto_approve: bool
    max_executions_per_hour: int
    cooldown_minutes: int
    last_executed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# Helper functions
def resolve_command_parameters(command: str, parameters: dict) -> str:
    """Replace {{param}} placeholders in command with values."""
    result = command
    for key, value in parameters.items():
        placeholder = "{{" + key + "}}"
        result = result.replace(placeholder, str(value))
    
    # Check for unresolved placeholders
    remaining = re.findall(r'\{\{(\w+)\}\}', result)
    if remaining:
        raise ValueError(f"Unresolved parameters: {', '.join(remaining)}")
    
    return result


def to_execution_response(e: CommandExecution) -> CommandExecutionResponse:
    """Convert CommandExecution model to response."""
    return CommandExecutionResponse(
        id=e.id,
        device_id=e.device_id,
        device_hostname=e.device.hostname if e.device else None,
        template_id=e.template_id,
        template_name=e.template.name if e.template else None,
        command=e.command,
        parameters=e.parameters,
        status=e.status,
        queued_at=e.queued_at,
        started_at=e.started_at,
        completed_at=e.completed_at,
        exit_code=e.exit_code,
        stdout=e.stdout,
        stderr=e.stderr,
        source=e.source,
        requested_by=e.requested_by
    )


# Command Template Endpoints
@router.post("/templates", response_model=CommandTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_command_template(
    data: CommandTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new command template."""
    # Check for duplicate name
    existing = db.query(CommandTemplate).filter(CommandTemplate.name == data.name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Template name already exists")
    
    template = CommandTemplate(
        name=data.name,
        description=data.description,
        command=data.command,
        command_type=data.command_type,
        requires_approval=data.requires_approval,
        allowed_roles=data.allowed_roles,
        max_execution_time=data.max_execution_time,
        parameters=json.dumps([p.dict() for p in data.parameters]) if data.parameters else None,
        allowed_hostgroups=data.allowed_hostgroups,
        created_by=current_user.id
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return template


@router.get("/templates", response_model=List[CommandTemplateResponse])
def list_command_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all command templates."""
    templates = db.query(CommandTemplate).order_by(CommandTemplate.name).all()
    return templates


@router.get("/templates/{template_id}", response_model=CommandTemplateResponse)
def get_command_template(
    template_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get command template details."""
    template = db.query(CommandTemplate).filter(CommandTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return template


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_command_template(
    template_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a command template."""
    template = db.query(CommandTemplate).filter(CommandTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    
    db.delete(template)
    db.commit()


# Command Execution Endpoints
@router.post("/execute", response_model=CommandExecutionResponse, status_code=status.HTTP_201_CREATED)
def queue_command_execution(
    data: ExecuteCommandRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Queue a command for execution on a device."""
    # Validate device
    device = db.query(Device).filter(Device.id == data.device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    
    # Resolve command
    template = None
    if data.template_id:
        template = db.query(CommandTemplate).filter(CommandTemplate.id == data.template_id).first()
        if not template:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
        
        # Resolve parameters
        params = data.parameters or {}
        try:
            resolved_command = resolve_command_parameters(template.command, params)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        
        requires_approval = template.requires_approval
    elif data.command:
        resolved_command = data.command
        requires_approval = True  # Always require approval for direct commands
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Either template_id or command must be provided"
        )
    
    # Create execution record
    execution = CommandExecution(
        template_id=data.template_id,
        device_id=data.device_id,
        command=resolved_command,
        parameters=json.dumps(data.parameters) if data.parameters else None,
        status="pending" if requires_approval else "approved",
        source="manual",
        requested_by=current_user.id
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    
    return to_execution_response(execution)


@router.get("/executions", response_model=List[CommandExecutionResponse])
def list_executions(
    status_filter: Optional[str] = None,
    device_id: Optional[UUID] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List command executions."""
    query = db.query(CommandExecution)
    
    if status_filter:
        query = query.filter(CommandExecution.status == status_filter)
    if device_id:
        query = query.filter(CommandExecution.device_id == device_id)
    
    executions = query.order_by(CommandExecution.queued_at.desc()).limit(limit).all()
    
    return [to_execution_response(e) for e in executions]


@router.get("/executions/pending", response_model=List[CommandExecutionResponse])
def list_pending_approvals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List executions pending approval."""
    executions = db.query(CommandExecution).filter(
        CommandExecution.status == "pending"
    ).order_by(CommandExecution.queued_at).all()
    
    return [to_execution_response(e) for e in executions]


@router.get("/executions/{execution_id}", response_model=CommandExecutionResponse)
def get_execution(
    execution_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get execution details."""
    execution = db.query(CommandExecution).filter(CommandExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    
    return to_execution_response(execution)


@router.post("/executions/{execution_id}/approve")
def approve_execution(
    execution_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Approve a pending command execution."""
    execution = db.query(CommandExecution).filter(CommandExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    
    if execution.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Execution is not pending")
    
    execution.status = "approved"
    execution.approved_by = current_user.id
    execution.approved_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Execution approved", "id": str(execution_id)}


@router.post("/executions/{execution_id}/reject")
def reject_execution(
    execution_id: UUID,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reject a pending command execution."""
    execution = db.query(CommandExecution).filter(CommandExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    
    if execution.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Execution is not pending")
    
    execution.status = "cancelled"
    execution.rejection_reason = reason
    db.commit()
    
    return {"message": "Execution rejected", "id": str(execution_id)}


# Agent polling endpoint (no auth for agent)
@router.get("/agent/{device_id}/pending")
def get_pending_commands_for_device(
    device_id: UUID,
    db: Session = Depends(get_db)
):
    """Get approved commands waiting to be executed on a device.
    
    Called by agents to poll for pending commands.
    """
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    
    executions = db.query(CommandExecution).filter(
        CommandExecution.device_id == device_id,
        CommandExecution.status == "approved"
    ).order_by(CommandExecution.queued_at).all()
    
    return [{
        "id": str(e.id),
        "command": e.command,
        "timeout": e.template.max_execution_time if e.template else 300
    } for e in executions]


@router.post("/agent/{device_id}/result")
def submit_command_result(
    device_id: UUID,
    execution_id: UUID,
    exit_code: int,
    stdout: Optional[str] = None,
    stderr: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Submit execution result from agent."""
    execution = db.query(CommandExecution).filter(
        CommandExecution.id == execution_id,
        CommandExecution.device_id == device_id
    ).first()
    
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    
    execution.status = "completed" if exit_code == 0 else "failed"
    execution.exit_code = exit_code
    execution.stdout = stdout
    execution.stderr = stderr
    execution.completed_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Result recorded", "status": execution.status}


# Remediation Rules Endpoints
@router.post("/remediation", response_model=RemediationRuleResponse, status_code=status.HTTP_201_CREATED)
def create_remediation_rule(
    data: RemediationRuleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create an auto-remediation rule."""
    # Validate trigger
    trigger = db.query(Trigger).filter(Trigger.id == data.trigger_id).first()
    if not trigger:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trigger not found")
    
    # Validate template
    template = db.query(CommandTemplate).filter(CommandTemplate.id == data.command_template_id).first()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Command template not found")
    
    rule = RemediationRule(
        name=data.name,
        description=data.description,
        trigger_id=data.trigger_id,
        command_template_id=data.command_template_id,
        enabled=data.enabled,
        auto_approve=data.auto_approve,
        max_executions_per_hour=data.max_executions_per_hour,
        cooldown_minutes=data.cooldown_minutes,
        created_by=current_user.id
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    
    return RemediationRuleResponse(
        id=rule.id,
        name=rule.name,
        description=rule.description,
        trigger_id=rule.trigger_id,
        trigger_name=trigger.name,
        command_template_id=rule.command_template_id,
        command_template_name=template.name,
        enabled=rule.enabled,
        auto_approve=rule.auto_approve,
        max_executions_per_hour=rule.max_executions_per_hour,
        cooldown_minutes=rule.cooldown_minutes,
        last_executed_at=rule.last_executed_at,
        created_at=rule.created_at
    )


@router.get("/remediation", response_model=List[RemediationRuleResponse])
def list_remediation_rules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all remediation rules."""
    rules = db.query(RemediationRule).order_by(RemediationRule.name).all()
    
    return [RemediationRuleResponse(
        id=r.id,
        name=r.name,
        description=r.description,
        trigger_id=r.trigger_id,
        trigger_name=r.trigger.name if r.trigger else None,
        command_template_id=r.command_template_id,
        command_template_name=r.command_template.name if r.command_template else None,
        enabled=r.enabled,
        auto_approve=r.auto_approve,
        max_executions_per_hour=r.max_executions_per_hour,
        cooldown_minutes=r.cooldown_minutes,
        last_executed_at=r.last_executed_at,
        created_at=r.created_at
    ) for r in rules]


@router.delete("/remediation/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_remediation_rule(
    rule_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a remediation rule."""
    rule = db.query(RemediationRule).filter(RemediationRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    
    db.delete(rule)
    db.commit()
