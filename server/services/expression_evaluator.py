"""Advanced expression evaluator for compound triggers."""
import logging
import json
import re
import operator
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from db.models import Trigger, Device

logger = logging.getLogger(__name__)


class ExpressionEvaluator:
    """
    Evaluates trigger expressions including:
    - Simple threshold expressions
    - Compound expressions (AND/OR combinations)
    - Time-based aggregations (avg, min, max over windows)
    - Duration requirements
    - Trigger dependencies
    """
    
    # Comparison operators
    OPERATORS = {
        '>': operator.gt,
        '<': operator.lt,
        '>=': operator.ge,
        '<=': operator.le,
        '=': operator.eq,
        '==': operator.eq,
        '!=': operator.ne,
        '<>': operator.ne,
    }
    
    # Time function mappings
    TIME_FUNCTIONS = {
        'avg': lambda values: sum(values) / len(values) if values else 0,
        'min': lambda values: min(values) if values else 0,
        'max': lambda values: max(values) if values else 0,
        'last': lambda values: values[-1] if values else 0,
        'first': lambda values: values[0] if values else 0,
        'sum': sum,
        'count': len,
        'diff': lambda values: abs(values[-1] - values[0]) if len(values) >= 2 else 0,
        'percentile90': lambda values: sorted(values)[int(len(values) * 0.9)] if values else 0,
    }
    
    def __init__(self, metrics_client=None):
        """
        Args:
            metrics_client: Client for querying VictoriaMetrics/Prometheus
        """
        self.metrics_client = metrics_client
        self._state_cache = {}  # trigger_id -> (state, since_timestamp)
    
    def parse_simple_expression(self, expression: str) -> Optional[Dict[str, Any]]:
        """
        Parse a simple expression like "{host:cpu.load}>80" or "cpu_load_avg > 80"
        
        Returns:
            Dict with 'metric', 'operator', 'threshold', 'function' keys
        """
        # Pattern: {host:metric.function(time)} operator value
        # or: metric operator value
        patterns = [
            # Zabbix-style: {host:cpu.load.avg(5m)}>80
            r'\{([^:]+):([^}]+)\}\s*([><=!]+)\s*([\d.]+)',
            # PromQL-style: avg_over_time(cpu_load[5m]) > 80
            r'(\w+_over_time)\(([^)]+)\)\s*([><=!]+)\s*([\d.]+)',
            # Simple: cpu_load > 80
            r'([a-zA-Z_][a-zA-Z0-9_]*)\s*([><=!]+)\s*([\d.]+)',
        ]
        
        for pattern in patterns:
            match = re.match(pattern, expression.strip())
            if match:
                groups = match.groups()
                if len(groups) == 4:
                    return {
                        'host': groups[0],
                        'metric': groups[1],
                        'operator': groups[2],
                        'threshold': float(groups[3])
                    }
                elif len(groups) == 3:
                    return {
                        'metric': groups[0],
                        'operator': groups[1],
                        'threshold': float(groups[2])
                    }
        
        logger.warning(f"Failed to parse expression: {expression}")
        return None
    
    def evaluate_simple(
        self, 
        expression: str, 
        current_value: float
    ) -> Tuple[bool, str]:
        """
        Evaluate a simple expression against a current value.
        
        Returns:
            Tuple of (is_problem: bool, state: str)
        """
        parsed = self.parse_simple_expression(expression)
        if not parsed:
            return False, "UNKNOWN"
        
        op_func = self.OPERATORS.get(parsed['operator'])
        if not op_func:
            logger.error(f"Unknown operator: {parsed['operator']}")
            return False, "UNKNOWN"
        
        threshold = parsed['threshold']
        is_problem = op_func(current_value, threshold)
        
        return is_problem, "PROBLEM" if is_problem else "OK"
    
    def evaluate_compound(
        self, 
        compound_expression: str, 
        values: Dict[str, float]
    ) -> Tuple[bool, str]:
        """
        Evaluate a compound expression (JSON format).
        
        Format:
        {
            "operator": "and" | "or",
            "conditions": [
                {"metric": "cpu_load", "operator": ">", "value": 80},
                {"metric": "memory_used", "operator": ">", "value": 90}
            ]
        }
        
        Args:
            compound_expression: JSON string
            values: Dict mapping metric names to current values
            
        Returns:
            Tuple of (is_problem: bool, state: str)
        """
        try:
            expr = json.loads(compound_expression)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid compound expression JSON: {e}")
            return False, "UNKNOWN"
        
        logical_op = expr.get('operator', 'and').lower()
        conditions = expr.get('conditions', [])
        
        if not conditions:
            return False, "OK"
        
        results = []
        for cond in conditions:
            metric = cond.get('metric')
            op_str = cond.get('operator', '>')
            threshold = float(cond.get('value', 0))
            
            current_value = values.get(metric)
            if current_value is None:
                logger.warning(f"No value for metric {metric}")
                results.append(False)
                continue
            
            op_func = self.OPERATORS.get(op_str)
            if op_func:
                results.append(op_func(float(current_value), threshold))
            else:
                results.append(False)
        
        if logical_op == 'and':
            is_problem = all(results)
        elif logical_op == 'or':
            is_problem = any(results)
        else:
            is_problem = results[0] if results else False
        
        return is_problem, "PROBLEM" if is_problem else "OK"
    
    def check_duration(
        self, 
        trigger: Trigger, 
        current_state: str, 
        db: Session
    ) -> bool:
        """
        Check if trigger has been in PROBLEM state long enough to fire.
        
        Args:
            trigger: The trigger being evaluated
            current_state: Current evaluated state
            db: Database session
            
        Returns:
            True if duration requirement is met (should alert)
        """
        if trigger.duration <= 0:
            return current_state == "PROBLEM"
        
        now = datetime.utcnow()
        
        # Check state transition
        if trigger.last_state != current_state:
            # State changed - update state_since
            trigger.state_since = now
            trigger.last_state = current_state
            db.flush()
        
        if current_state != "PROBLEM":
            return False
        
        # Check if we've been in PROBLEM state long enough
        if trigger.state_since:
            duration_met = (now - trigger.state_since).total_seconds() >= trigger.duration
            if duration_met:
                logger.debug(f"Trigger {trigger.name} duration requirement met ({trigger.duration}s)")
            return duration_met
        
        return False
    
    def check_dependencies(
        self, 
        trigger: Trigger, 
        db: Session
    ) -> bool:
        """
        Check if parent trigger is in OK state (dependency check).
        
        If parent trigger is in PROBLEM state, suppress this trigger.
        
        Returns:
            True if this trigger should be evaluated (no blocked dependencies)
        """
        if not trigger.parent_trigger_id:
            return True
        
        parent = trigger.parent_trigger
        if not parent:
            return True
        
        # If parent is in PROBLEM state, suppress child triggers
        if parent.last_state == "PROBLEM":
            logger.debug(
                f"Trigger {trigger.name} suppressed - parent {parent.name} in PROBLEM state"
            )
            return False
        
        return True
    
    def evaluate_recovery(
        self, 
        trigger: Trigger, 
        current_value: float
    ) -> bool:
        """
        Evaluate recovery expression (for hysteresis).
        
        Returns:
            True if trigger should recover to OK state
        """
        if not trigger.recovery_expression:
            # Use inverse of main expression
            is_problem, _ = self.evaluate_simple(trigger.expression, current_value)
            return not is_problem
        
        # Evaluate separate recovery expression
        is_recovered, _ = self.evaluate_simple(trigger.recovery_expression, current_value)
        return is_recovered
    
    async def evaluate_trigger(
        self, 
        trigger: Trigger, 
        db: Session,
        device: Optional[Device] = None,
        current_values: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Full evaluation of a trigger.
        
        Returns:
            Dict with:
                - should_alert: bool
                - state: "OK" | "PROBLEM" | "UNKNOWN"
                - value: current metric value
                - message: description
        """
        now = datetime.utcnow()
        result = {
            'should_alert': False,
            'state': 'UNKNOWN',
            'value': None,
            'message': ''
        }
        
        # Check dependencies first
        if not self.check_dependencies(trigger, db):
            result['message'] = f"Suppressed by parent trigger"
            result['state'] = 'OK'
            return result
        
        # Evaluate based on expression type
        if trigger.expression_type == 'compound' and trigger.compound_expression:
            if current_values:
                is_problem, state = self.evaluate_compound(
                    trigger.compound_expression, 
                    current_values
                )
            else:
                result['message'] = "No values provided for compound expression"
                return result
        else:
            # Simple expression - need single value
            value = current_values.get('value') if current_values else None
            if value is None:
                result['message'] = "No value available"
                return result
            
            result['value'] = value
            is_problem, state = self.evaluate_simple(trigger.expression, value)
        
        result['state'] = state
        
        # Check if currently in PROBLEM and attempting recovery
        if trigger.last_state == "PROBLEM" and not is_problem:
            # Check recovery expression (hysteresis)
            if current_values and 'value' in current_values:
                if not self.evaluate_recovery(trigger, current_values['value']):
                    # Don't recover yet - hysteresis
                    result['state'] = 'PROBLEM'
                    result['message'] = "Recovery threshold not met"
                    return result
        
        # Check duration requirement
        if trigger.duration > 0:
            should_alert = self.check_duration(trigger, state, db)
        else:
            should_alert = is_problem
        
        # Update trigger state
        trigger.last_evaluated_at = now
        if trigger.last_state != state:
            trigger.state_since = now
        trigger.last_state = state
        
        # Determine if we should create an alert
        result['should_alert'] = should_alert and state == "PROBLEM"
        result['message'] = f"Trigger {trigger.name}: {state}"
        
        if result['value'] is not None:
            result['message'] += f" (value: {result['value']})"
        
        return result


# Singleton instance
expression_evaluator = ExpressionEvaluator()
