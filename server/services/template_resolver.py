"""Template resolver service - Resolves inheritance and merges configurations."""
import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_

from db.models import Template, TemplateItem, Device, HostGroup, device_template

logger = logging.getLogger(__name__)

# Maximum inheritance depth to prevent infinite loops
MAX_INHERITANCE_DEPTH = 10


class TemplateResolver:
    """Resolves template inheritance chains and merges configurations."""
    
    def resolve_template_chain(self, template: Template, db: Session) -> List[Template]:
        """
        Walk the parent chain and return ordered list of templates.
        
        The order is from root parent to the current template (child last).
        Child templates override parent configurations.
        
        Args:
            template: Starting template
            db: Database session
            
        Returns:
            List of templates from root parent to child
            
        Raises:
            ValueError: If circular reference or max depth exceeded
        """
        chain = []
        current = template
        visited = set()
        depth = 0
        
        while current is not None:
            if depth > MAX_INHERITANCE_DEPTH:
                raise ValueError(f"Template inheritance depth exceeds maximum ({MAX_INHERITANCE_DEPTH})")
            
            if current.id in visited:
                raise ValueError(f"Circular template reference detected: {current.name}")
            
            visited.add(current.id)
            chain.append(current)
            current = current.parent_template
            depth += 1
        
        # Reverse so parent comes first (parent configs get overridden by child)
        return list(reversed(chain))
    
    def merge_template_items(self, templates: List[Template]) -> Dict[str, TemplateItem]:
        """
        Merge items from template chain, child overrides parent.
        
        Uses the item 'key' as the unique identifier for merging.
        
        Args:
            templates: Ordered list from parent to child
            
        Returns:
            Dict mapping item key to the effective TemplateItem
        """
        merged_items = {}
        
        for template in templates:
            for item in template.items:
                # Child items override parent items with same key
                merged_items[item.key] = item
        
        return merged_items
    
    def get_device_templates(self, device: Device, db: Session) -> List[Template]:
        """
        Get all templates applicable to a device.
        
        Priority order (highest to lowest):
        1. Direct device-to-template assignments (by priority DESC)
        2. Templates via host group membership
        
        Args:
            device: The device to get templates for
            db: Database session
            
        Returns:
            Ordered list of templates (lower priority first, higher priority last)
        """
        templates = []
        seen_template_ids = set()
        
        # 1. Templates from host groups (lower priority, applied first)
        for hostgroup in device.host_groups:
            for template in hostgroup.templates:
                if template.id not in seen_template_ids:
                    templates.append((template, 0))  # priority 0 for hostgroup
                    seen_template_ids.add(template.id)
        
        # 2. Direct device assignments (higher priority, override hostgroup)
        # Query device_template table for assignments with priority
        direct_assignments = db.execute(
            device_template.select().where(
                device_template.c.device_id == device.id
            ).order_by(device_template.c.priority.asc())
        ).fetchall()
        
        for assignment in direct_assignments:
            template = db.query(Template).filter(Template.id == assignment.template_id).first()
            if template:
                if template.id in seen_template_ids:
                    # Remove from lower priority position
                    templates = [(t, p) for t, p in templates if t.id != template.id]
                templates.append((template, assignment.priority + 100))  # +100 to ensure above hostgroup
                seen_template_ids.add(template.id)
        
        # Sort by priority and return just templates
        templates.sort(key=lambda x: x[1])
        return [t for t, _ in templates]
    
    def get_effective_config(self, device: Device, db: Session) -> Dict[str, Any]:
        """
        Get the final merged configuration for a device.
        
        This resolves all templates (with inheritance) and merges their items.
        
        Args:
            device: Device to get config for
            db: Database session
            
        Returns:
            Dict with:
                - items: List of effective template items
                - templates: List of template names applied
                - triggers: List of effective triggers
        """
        config = {
            'items': [],
            'templates': [],
            'triggers': [],
            'device_id': str(device.id),
            'hostname': device.hostname
        }
        
        final_items = {}  # key -> TemplateItem
        all_triggers = []
        
        # Get all templates for this device
        device_templates = self.get_device_templates(device, db)
        
        for template in device_templates:
            # Resolve inheritance chain for each template
            try:
                chain = self.resolve_template_chain(template, db)
                config['templates'].extend([t.name for t in chain if t.name not in config['templates']])
                
                # Merge items from chain
                chain_items = self.merge_template_items(chain)
                final_items.update(chain_items)
                
                # Collect triggers from chain
                for t in chain:
                    for trigger in t.triggers:
                        if trigger.enabled:
                            all_triggers.append({
                                'id': str(trigger.id),
                                'name': trigger.name,
                                'expression': trigger.expression,
                                'severity': trigger.severity,
                                'template': t.name
                            })
            except ValueError as e:
                logger.error(f"Error resolving template chain for {template.name}: {e}")
                continue
        
        # Convert items to serializable format
        for key, item in final_items.items():
            if item.enabled:
                config['items'].append({
                    'key': item.key,
                    'name': item.name,
                    'value_type': item.value_type,
                    'units': item.units,
                    'update_interval': item.update_interval
                })
        
        config['triggers'] = all_triggers
        
        return config
    
    def assign_template_to_device(
        self, 
        db: Session, 
        device_id: str, 
        template_id: str, 
        priority: int = 0
    ) -> bool:
        """
        Assign a template directly to a device.
        
        Args:
            db: Database session
            device_id: UUID of device
            template_id: UUID of template
            priority: Assignment priority (higher overrides lower)
            
        Returns:
            True if successful
        """
        from datetime import datetime

        try:
            device_uuid = UUID(str(device_id))
            template_uuid = UUID(str(template_id))
        except ValueError:
            logger.error(f"Invalid device/template id for assignment: {device_id}, {template_id}")
            return False
        
        # Check if already exists
        existing = db.execute(
            device_template.select().where(
                and_(
                    device_template.c.device_id == device_uuid,
                    device_template.c.template_id == template_uuid
                )
            )
        ).first()
        
        if existing:
            # Update priority
            db.execute(
                device_template.update().where(
                    and_(
                        device_template.c.device_id == device_uuid,
                        device_template.c.template_id == template_uuid
                    )
                ).values(priority=priority)
            )
        else:
            # Insert new assignment
            db.execute(
                device_template.insert().values(
                    device_id=device_uuid,
                    template_id=template_uuid,
                    priority=priority,
                    assigned_at=datetime.utcnow()
                )
            )
        
        db.commit()
        logger.info(f"Assigned template {template_id} to device {device_id} with priority {priority}")
        return True
    
    def unassign_template_from_device(self, db: Session, device_id: str, template_id: str) -> bool:
        """Remove a direct template assignment from a device."""
        try:
            device_uuid = UUID(str(device_id))
            template_uuid = UUID(str(template_id))
        except ValueError:
            logger.error(f"Invalid device/template id for unassignment: {device_id}, {template_id}")
            return False
        db.execute(
            device_template.delete().where(
                and_(
                    device_template.c.device_id == device_uuid,
                    device_template.c.template_id == template_uuid
                )
            )
        )
        db.commit()
        logger.info(f"Unassigned template {template_id} from device {device_id}")
        return True


# Singleton instance
template_resolver = TemplateResolver()
