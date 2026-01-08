"""Maintenance service - Manages maintenance windows and alert suppression."""
import logging
from datetime import datetime
from typing import Optional, Set, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from db.models import MaintenanceWindow, Device, HostGroup

logger = logging.getLogger(__name__)


class MaintenanceService:
    """Manages maintenance windows and alert suppression."""
    
    def is_device_in_maintenance(self, device_id: str, db: Session) -> bool:
        """
        Check if a device is currently in an active maintenance window.
        
        Args:
            device_id: UUID of the device to check
            db: Database session
            
        Returns:
            True if device is in maintenance, False otherwise
        """
        now = datetime.utcnow()
        
        # Get the device to find its host groups
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            return False
        
        # Get device's host group IDs
        hostgroup_ids = [hg.id for hg in device.host_groups]
        
        # Query for active maintenance windows that cover this device
        query = db.query(MaintenanceWindow).filter(
            MaintenanceWindow.active == True,
            MaintenanceWindow.start_time <= now,
            MaintenanceWindow.end_time >= now,
            or_(
                # Scope: all devices
                MaintenanceWindow.scope_type == 'all',
                # Scope: this specific device
                and_(
                    MaintenanceWindow.scope_type == 'device',
                    MaintenanceWindow.device_id == device_id
                ),
                # Scope: a host group this device belongs to
                and_(
                    MaintenanceWindow.scope_type == 'hostgroup',
                    MaintenanceWindow.hostgroup_id.in_(hostgroup_ids)
                ) if hostgroup_ids else False
            )
        )
        
        window = query.first()
        
        if window:
            logger.debug(f"Device {device_id} is in maintenance window '{window.name}'")
            return True
        
        return False
    
    def get_active_windows(self, db: Session) -> List[MaintenanceWindow]:
        """
        Get all currently active maintenance windows.
        
        Returns:
            List of active maintenance windows
        """
        now = datetime.utcnow()
        
        return db.query(MaintenanceWindow).filter(
            MaintenanceWindow.active == True,
            MaintenanceWindow.start_time <= now,
            MaintenanceWindow.end_time >= now
        ).all()
    
    def get_suppressed_devices(self, db: Session) -> Set[str]:
        """
        Get set of device IDs currently in maintenance.
        
        Returns:
            Set of device UUIDs that should have alerts suppressed
        """
        now = datetime.utcnow()
        suppressed = set()
        
        # Get all active windows
        active_windows = db.query(MaintenanceWindow).filter(
            MaintenanceWindow.active == True,
            MaintenanceWindow.start_time <= now,
            MaintenanceWindow.end_time >= now
        ).all()
        
        for window in active_windows:
            if window.scope_type == 'all':
                # All devices are suppressed - get all device IDs
                all_devices = db.query(Device.id).all()
                suppressed.update(str(d.id) for d in all_devices)
            elif window.scope_type == 'device' and window.device_id:
                suppressed.add(str(window.device_id))
            elif window.scope_type == 'hostgroup' and window.hostgroup_id:
                # Get all devices in this host group
                hostgroup = db.query(HostGroup).filter(
                    HostGroup.id == window.hostgroup_id
                ).first()
                if hostgroup:
                    suppressed.update(str(d.id) for d in hostgroup.devices)
        
        return suppressed
    
    def should_collect_data(self, device_id: str, db: Session) -> bool:
        """
        Check if data should be collected for a device during maintenance.
        
        Some maintenance windows may want to suppress alerts but still collect data.
        
        Returns:
            False if device is in a 'no data collection' maintenance window
        """
        now = datetime.utcnow()
        
        # Get the device to find its host groups
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            return True  # Default to collecting data
        
        hostgroup_ids = [hg.id for hg in device.host_groups]
        
        # Look for any maintenance window with collect_data=False
        query = db.query(MaintenanceWindow).filter(
            MaintenanceWindow.active == True,
            MaintenanceWindow.start_time <= now,
            MaintenanceWindow.end_time >= now,
            MaintenanceWindow.collect_data == False,
            or_(
                MaintenanceWindow.scope_type == 'all',
                and_(
                    MaintenanceWindow.scope_type == 'device',
                    MaintenanceWindow.device_id == device_id
                ),
                and_(
                    MaintenanceWindow.scope_type == 'hostgroup',
                    MaintenanceWindow.hostgroup_id.in_(hostgroup_ids)
                ) if hostgroup_ids else False
            )
        )
        
        if query.first():
            return False  # Don't collect data
        
        return True  # Collect data normally
    
    def create_window(
        self,
        db: Session,
        name: str,
        start_time: datetime,
        end_time: datetime,
        scope_type: str = 'all',
        device_id: Optional[str] = None,
        hostgroup_id: Optional[str] = None,
        description: Optional[str] = None,
        recurrence: Optional[str] = None,
        collect_data: bool = True,
        created_by: Optional[str] = None
    ) -> MaintenanceWindow:
        """
        Create a new maintenance window.
        
        Args:
            db: Database session
            name: Name of the maintenance window
            start_time: When maintenance starts
            end_time: When maintenance ends
            scope_type: 'all', 'device', or 'hostgroup'
            device_id: Device UUID if scope_type is 'device'
            hostgroup_id: HostGroup UUID if scope_type is 'hostgroup'
            description: Optional description
            recurrence: Cron expression for recurring windows
            collect_data: Whether to collect data during maintenance
            created_by: User UUID who created this window
            
        Returns:
            Created MaintenanceWindow object
        """
        window = MaintenanceWindow(
            name=name,
            description=description,
            start_time=start_time,
            end_time=end_time,
            recurrence=recurrence,
            scope_type=scope_type,
            device_id=device_id,
            hostgroup_id=hostgroup_id,
            collect_data=collect_data,
            created_by=created_by
        )
        
        db.add(window)
        db.commit()
        db.refresh(window)
        
        logger.info(f"Created maintenance window '{name}' ({scope_type}) from {start_time} to {end_time}")
        return window


# Singleton instance
maintenance_service = MaintenanceService()
