"""API endpoints for Network Discovery management."""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import List, Optional

from db.models import get_db, DiscoveryJob, DiscoveryResult, Device, HostGroup, User
from api.auth import get_current_user
from services.network_scanner import network_scanner

router = APIRouter(prefix="/discovery", tags=["Discovery"])


# Pydantic Models
class DiscoveryJobCreate(BaseModel):
    name: str
    description: Optional[str] = None
    ip_ranges: str  # Comma-separated CIDR ranges
    
    # Scan options
    scan_icmp: Optional[bool] = True
    scan_snmp: Optional[bool] = False
    snmp_community: Optional[str] = "public"
    snmp_version: Optional[str] = "2c"
    scan_ports: Optional[str] = None  # Comma-separated ports
    
    # Schedule
    schedule_type: Optional[str] = "manual"
    schedule_cron: Optional[str] = None
    
    # Auto-add
    auto_add_devices: Optional[bool] = False
    auto_add_hostgroup_id: Optional[UUID] = None


class DiscoveryJobUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    ip_ranges: Optional[str] = None
    scan_icmp: Optional[bool] = None
    scan_snmp: Optional[bool] = None
    snmp_community: Optional[str] = None
    scan_ports: Optional[str] = None
    schedule_type: Optional[str] = None
    schedule_cron: Optional[str] = None
    auto_add_devices: Optional[bool] = None
    auto_add_hostgroup_id: Optional[UUID] = None


class DiscoveryResultResponse(BaseModel):
    id: UUID
    ip_address: str
    hostname: Optional[str]
    mac_address: Optional[str]
    icmp_reachable: Optional[bool]
    icmp_latency_ms: Optional[int]
    snmp_reachable: Optional[bool]
    snmp_sysname: Optional[str]
    snmp_sysdescr: Optional[str]
    open_ports: Optional[str]
    status: str
    device_id: Optional[UUID]
    discovered_at: datetime

    class Config:
        from_attributes = True


class DiscoveryJobResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    ip_ranges: str
    scan_icmp: bool
    scan_snmp: bool
    scan_ports: Optional[str]
    schedule_type: str
    schedule_cron: Optional[str]
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    progress_percent: int
    error_message: Optional[str]
    auto_add_devices: bool
    auto_add_hostgroup_id: Optional[UUID]
    created_at: datetime
    results_count: int = 0

    class Config:
        from_attributes = True


class DiscoveryJobListResponse(BaseModel):
    jobs: List[DiscoveryJobResponse]
    total: int


class DeviceAddRequest(BaseModel):
    result_ids: List[UUID]
    hostgroup_id: Optional[UUID] = None


class DeviceAddResponse(BaseModel):
    added: int
    device_ids: List[UUID]


def to_job_response(job: DiscoveryJob) -> DiscoveryJobResponse:
    """Convert DiscoveryJob model to response."""
    return DiscoveryJobResponse(
        id=job.id,
        name=job.name,
        description=job.description,
        ip_ranges=job.ip_ranges,
        scan_icmp=job.scan_icmp,
        scan_snmp=job.scan_snmp,
        scan_ports=job.scan_ports,
        schedule_type=job.schedule_type,
        schedule_cron=job.schedule_cron,
        status=job.status,
        started_at=job.started_at,
        completed_at=job.completed_at,
        progress_percent=job.progress_percent or 0,
        error_message=job.error_message,
        auto_add_devices=job.auto_add_devices,
        auto_add_hostgroup_id=job.auto_add_hostgroup_id,
        created_at=job.created_at,
        results_count=len(job.results) if job.results else 0
    )


# Endpoints
@router.post("", response_model=DiscoveryJobResponse, status_code=status.HTTP_201_CREATED)
def create_discovery_job(
    data: DiscoveryJobCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new network discovery job."""
    # Validate hostgroup if provided
    if data.auto_add_hostgroup_id:
        hostgroup = db.query(HostGroup).filter(HostGroup.id == data.auto_add_hostgroup_id).first()
        if not hostgroup:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Host group not found")
    
    job = DiscoveryJob(
        name=data.name,
        description=data.description,
        ip_ranges=data.ip_ranges,
        scan_icmp=data.scan_icmp,
        scan_snmp=data.scan_snmp,
        snmp_community=data.snmp_community,
        snmp_version=data.snmp_version,
        scan_ports=data.scan_ports,
        schedule_type=data.schedule_type,
        schedule_cron=data.schedule_cron,
        auto_add_devices=data.auto_add_devices,
        auto_add_hostgroup_id=data.auto_add_hostgroup_id,
        created_by=current_user.id
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    return to_job_response(job)


@router.get("", response_model=DiscoveryJobListResponse)
def list_discovery_jobs(
    skip: int = 0,
    limit: int = 50,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all discovery jobs."""
    query = db.query(DiscoveryJob)
    
    if status_filter:
        query = query.filter(DiscoveryJob.status == status_filter)
    
    total = query.count()
    jobs = query.order_by(DiscoveryJob.created_at.desc()).offset(skip).limit(limit).all()
    
    return DiscoveryJobListResponse(
        jobs=[to_job_response(j) for j in jobs],
        total=total
    )


@router.get("/{job_id}", response_model=DiscoveryJobResponse)
def get_discovery_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get discovery job details."""
    job = db.query(DiscoveryJob).filter(DiscoveryJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discovery job not found")
    
    return to_job_response(job)


@router.get("/{job_id}/results", response_model=List[DiscoveryResultResponse])
def get_discovery_results(
    job_id: UUID,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get discovery results for a job."""
    job = db.query(DiscoveryJob).filter(DiscoveryJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discovery job not found")
    
    query = db.query(DiscoveryResult).filter(DiscoveryResult.job_id == job_id)
    
    if status_filter:
        query = query.filter(DiscoveryResult.status == status_filter)
    
    results = query.order_by(DiscoveryResult.ip_address).all()
    
    return [DiscoveryResultResponse(
        id=r.id,
        ip_address=r.ip_address,
        hostname=r.hostname,
        mac_address=r.mac_address,
        icmp_reachable=r.icmp_reachable,
        icmp_latency_ms=r.icmp_latency_ms,
        snmp_reachable=r.snmp_reachable,
        snmp_sysname=r.snmp_sysname,
        snmp_sysdescr=r.snmp_sysdescr,
        open_ports=r.open_ports,
        status=r.status,
        device_id=r.device_id,
        discovered_at=r.discovered_at
    ) for r in results]


async def run_job_background(job_id: str, db_url: str):
    """Background task to run discovery job."""
    import asyncio
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        job = db.query(DiscoveryJob).filter(DiscoveryJob.id == job_id).first()
        if job:
            await network_scanner.run_discovery(job, db)
    except Exception as e:
        job = db.query(DiscoveryJob).filter(DiscoveryJob.id == job_id).first()
        if job:
            job.status = 'failed'
            job.error_message = str(e)
            db.commit()
    finally:
        db.close()


@router.post("/{job_id}/run")
async def run_discovery_job(
    job_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start a discovery job (runs in background)."""
    job = db.query(DiscoveryJob).filter(DiscoveryJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discovery job not found")
    
    if job.status == 'running':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job is already running")
    
    # Reset job status
    job.status = 'pending'
    job.progress_percent = 0
    job.error_message = None
    db.commit()
    
    # Run in background
    import os
    db_url = os.getenv("DATABASE_URL", "postgresql://health_check:health_check@localhost:5432/health_check_db")
    background_tasks.add_task(run_job_background, str(job_id), db_url)
    
    return {"message": "Discovery job started", "job_id": str(job_id)}


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_discovery_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a discovery job and its results."""
    job = db.query(DiscoveryJob).filter(DiscoveryJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discovery job not found")
    
    if job.status == 'running':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete running job")
    
    db.delete(job)
    db.commit()


@router.post("/{job_id}/add-devices", response_model=DeviceAddResponse)
def add_discovered_devices(
    job_id: UUID,
    data: DeviceAddRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add discovered hosts as devices."""
    job = db.query(DiscoveryJob).filter(DiscoveryJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discovery job not found")
    
    # Validate hostgroup if provided
    hostgroup = None
    if data.hostgroup_id:
        hostgroup = db.query(HostGroup).filter(HostGroup.id == data.hostgroup_id).first()
        if not hostgroup:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Host group not found")
    
    added_ids = []
    for result_id in data.result_ids:
        result = db.query(DiscoveryResult).filter(
            DiscoveryResult.id == result_id,
            DiscoveryResult.job_id == job_id
        ).first()
        
        if result and result.status == 'new':
            # Check if device already exists with this IP
            existing = db.query(Device).filter(Device.ip_address == result.ip_address).first()
            if existing:
                result.status = 'existing'
                result.device_id = existing.id
                continue
            
            # Create new device
            device = Device(
                hostname=result.hostname or result.ip_address,
                ip_address=result.ip_address,
                status='unknown',
                agent_type='discovered'
            )
            db.add(device)
            db.flush()
            
            # Add to hostgroup if specified
            if hostgroup:
                device.host_groups.append(hostgroup)
            
            # Update result
            result.status = 'added'
            result.device_id = device.id
            added_ids.append(device.id)
    
    db.commit()
    
    return DeviceAddResponse(added=len(added_ids), device_ids=added_ids)


@router.post("/{job_id}/results/{result_id}/ignore")
def ignore_discovery_result(
    job_id: UUID,
    result_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a discovery result as ignored."""
    result = db.query(DiscoveryResult).filter(
        DiscoveryResult.id == result_id,
        DiscoveryResult.job_id == job_id
    ).first()
    
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discovery result not found")
    
    result.status = 'ignored'
    db.commit()
    
    return {"message": "Result marked as ignored", "ip_address": result.ip_address}
