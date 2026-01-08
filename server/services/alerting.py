"""Alerting service - Trigger evaluation and alert event creation."""
import os
import re
import logging
from decimal import Decimal
from typing import Optional, Dict
import httpx
from sqlalchemy.orm import Session

from db.models import Trigger, AlertEvent, Device
from services.maintenance import maintenance_service

logger = logging.getLogger(__name__)

VM_URL = os.getenv("VM_URL", "http://localhost:9090")


class TriggerEvaluator:
    """Evaluates triggers against VictoriaMetrics and manages state."""

    def __init__(self, vm_url: str = VM_URL):
        self.vm_url = vm_url
        self.trigger_states: Dict[str, str] = {}  # trigger_id -> "OK" | "PROBLEM"

    async def query_vm(self, expression: str) -> Optional[float]:
        """Query VictoriaMetrics for a metric value."""
        # Extract just the metric name (before comparison operator)
        metric_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)', expression)
        if not metric_match:
            logger.warning(f"Could not extract metric from expression: {expression}")
            return None

        metric_name = metric_match.group(1)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.vm_url}/api/v1/query",
                    params={"query": metric_name}
                )
                response.raise_for_status()
                data = response.json()

                if data.get("status") == "success":
                    results = data.get("data", {}).get("result", [])
                    if results:
                        # Return the first result's value
                        value_pair = results[0].get("value", [])
                        if len(value_pair) >= 2:
                            return float(value_pair[1])
                return None
        except Exception as e:
            logger.error(f"Failed to query VictoriaMetrics: {e}")
            return None

    def parse_threshold(self, expression: str, value: float) -> str:
        """Parse threshold from expression and determine state.
        
        Supports: >, <, >=, <=, ==
        Examples: "cpu_percent > 90", "memory_usage >= 80", "disk_free < 10"
        """
        match = re.search(r'([><=]+)\s*([\d.]+)\s*$', expression)
        if match:
            op, threshold = match.group(1), float(match.group(2))
            if op == '>' and value > threshold:
                return "PROBLEM"
            elif op == '>=' and value >= threshold:
                return "PROBLEM"
            elif op == '<' and value < threshold:
                return "PROBLEM"
            elif op == '<=' and value <= threshold:
                return "PROBLEM"
            elif op == '==' and value == threshold:
                return "PROBLEM"
        else:
            # Fallback: any non-zero value is PROBLEM
            logger.warning(f"Could not parse threshold from expression: {expression}")
            return "PROBLEM" if value > 0 else "OK"
        return "OK"

    async def evaluate_trigger(self, db: Session, trigger: Trigger, device_id: Optional[str] = None) -> Optional[AlertEvent]:
        """Evaluate a single trigger against VictoriaMetrics.
        
        Args:
            db: Database session
            trigger: Trigger to evaluate
            device_id: Optional device ID for device-specific triggers
        """
        # Check if device is in maintenance (suppress alerts if so)
        if device_id and maintenance_service.is_device_in_maintenance(device_id, db):
            logger.debug(f"Suppressing trigger '{trigger.name}' evaluation - device {device_id} in maintenance")
            return None
        
        # Query VictoriaMetrics
        value = await self.query_vm(trigger.expression)

        if value is None:
            return None

        # Determine new state
        new_state = self.parse_threshold(trigger.expression, value)
        old_state = self.trigger_states.get(str(trigger.id), "OK")

        # State changed?
        if new_state != old_state:
            self.trigger_states[str(trigger.id)] = new_state
            
            # Create alert event
            event = AlertEvent(
                trigger_id=trigger.id,
                device_id=device_id,
                status=new_state,
                value=Decimal(str(value)),
                message=f"Trigger '{trigger.name}' changed to {new_state}. Value: {value}"
            )
            db.add(event)
            db.commit()
            db.refresh(event)
            
            logger.info(f"Trigger {trigger.name} state changed: {old_state} -> {new_state}")
            return event

        return None

    async def evaluate_all_triggers(self, db: Session) -> list[AlertEvent]:
        """Evaluate all enabled triggers."""
        triggers = db.query(Trigger).filter(Trigger.enabled == True).all()
        events = []

        for trigger in triggers:
            try:
                event = await self.evaluate_trigger(db, trigger)
                if event:
                    events.append(event)
            except Exception as e:
                logger.error(f"Error evaluating trigger {trigger.id}: {e}")

        return events
