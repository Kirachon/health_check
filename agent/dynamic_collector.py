"""Dynamic metric collector - Collects metrics based on server-provided configuration."""
import logging
from typing import Dict, Any, List, Optional
import psutil

from config_sync import ConfigSync, ConfigItem

logger = logging.getLogger(__name__)


class DynamicCollector:
    """Collects metrics based on dynamically fetched configuration."""
    
    # Map of supported metric keys to collection functions
    METRIC_HANDLERS = {
        "system.cpu.percent": lambda: psutil.cpu_percent(interval=0.1),
        "system.cpu.load.1m": lambda: psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0,
        "system.cpu.load.5m": lambda: psutil.getloadavg()[1] if hasattr(psutil, 'getloadavg') else 0,
        "system.cpu.load.15m": lambda: psutil.getloadavg()[2] if hasattr(psutil, 'getloadavg') else 0,
        "system.memory.percent": lambda: psutil.virtual_memory().percent,
        "system.memory.used": lambda: psutil.virtual_memory().used,
        "system.memory.available": lambda: psutil.virtual_memory().available,
        "system.memory.total": lambda: psutil.virtual_memory().total,
        "system.swap.percent": lambda: psutil.swap_memory().percent,
        "system.swap.used": lambda: psutil.swap_memory().used,
        "system.disk.percent": lambda: psutil.disk_usage('/').percent,
        "system.disk.used": lambda: psutil.disk_usage('/').used,
        "system.disk.free": lambda: psutil.disk_usage('/').free,
        "system.disk.total": lambda: psutil.disk_usage('/').total,
        "system.net.bytes_sent": lambda: psutil.net_io_counters().bytes_sent,
        "system.net.bytes_recv": lambda: psutil.net_io_counters().bytes_recv,
        "system.uptime": lambda: _get_uptime(),
        "system.process.count": lambda: len(psutil.pids()),
    }
    
    def __init__(self, config_sync: ConfigSync):
        self.config_sync = config_sync
    
    def collect_item(self, item: ConfigItem) -> Optional[float]:
        """Collect a single metric item."""
        handler = self.METRIC_HANDLERS.get(item.key)
        
        if handler:
            try:
                value = handler()
                logger.debug(f"Collected {item.key}: {value}")
                return float(value)
            except Exception as e:
                logger.error(f"Error collecting {item.key}: {e}")
                return None
        else:
            logger.warning(f"Unknown metric key: {item.key}")
            return None
    
    async def collect_all(self) -> Dict[str, float]:
        """Collect all configured metrics.
        
        Returns a dict mapping metric keys to their values.
        """
        metrics = {}
        
        for item in self.config_sync.items:
            value = self.collect_item(item)
            if value is not None:
                metrics[item.key] = value
        
        return metrics
    
    def collect_all_sync(self) -> Dict[str, float]:
        """Synchronous version of collect_all."""
        metrics = {}
        
        for item in self.config_sync.items:
            value = self.collect_item(item)
            if value is not None:
                metrics[item.key] = value
        
        return metrics
    
    def get_collection_intervals(self) -> List[int]:
        """Get unique collection intervals from config."""
        return list(set(item.interval for item in self.config_sync.items))


def _get_uptime() -> float:
    """Get system uptime in seconds."""
    import time
    boot_time = psutil.boot_time()
    return time.time() - boot_time
