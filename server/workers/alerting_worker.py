"""Alerting background worker - Continuous trigger evaluation loop."""
import os
import asyncio
import logging
from contextlib import closing

from db.models import SessionLocal
from services.alerting import TriggerEvaluator

logger = logging.getLogger(__name__)

ALERTING_INTERVAL = int(os.getenv("ALERTING_INTERVAL", "60"))


async def alerting_loop():
    """Main alerting loop - evaluates all triggers continuously."""
    logger.info(f"Starting alerting worker (interval: {ALERTING_INTERVAL}s)")
    
    evaluator = TriggerEvaluator()
    
    while True:
        try:
            with closing(SessionLocal()) as db:
                events = await evaluator.evaluate_all_triggers(db)
                if events:
                    logger.info(f"Generated {len(events)} alert events")
        except Exception as e:
            logger.error(f"Error in alerting loop: {e}", exc_info=True)
        
        await asyncio.sleep(ALERTING_INTERVAL)
