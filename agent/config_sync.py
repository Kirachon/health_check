"""Config sync - Fetches configuration from server for dynamic metric collection."""
import os
import logging
from typing import Optional, Dict, Any, List
import httpx

logger = logging.getLogger(__name__)


class ConfigItem:
    """Represents a single metric collection item."""
    
    def __init__(self, key: str, item_type: str = "numeric", interval: int = 60, parameters: dict = None):
        self.key = key
        self.type = item_type
        self.interval = interval
        self.parameters = parameters or {}
    
    def __repr__(self):
        return f"ConfigItem(key={self.key}, type={self.type}, interval={self.interval})"


class ConfigSync:
    """Synchronizes agent configuration from the server."""
    
    def __init__(self, server_url: str, device_id: str, auth_token: str):
        self.server_url = server_url.rstrip('/')
        self.device_id = device_id
        self.auth_token = auth_token
        self.items: List[ConfigItem] = []
        self.last_updated: Optional[str] = None
    
    async def fetch_config(self) -> bool:
        """Fetch configuration from server.
        
        Returns True if config was updated, False otherwise.
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.server_url}/api/v1/templates/agents/{self.device_id}/config",
                    headers={"Authorization": f"Bearer {self.auth_token}"}
                )
                
                if response.status_code == 404:
                    logger.warning(f"Device {self.device_id} not found on server")
                    return False
                
                response.raise_for_status()
                data = response.json()
                
                # Check if config changed
                if data.get("updated_at") == self.last_updated:
                    logger.debug("Config unchanged")
                    return False
                
                # Parse items
                self.items = [
                    ConfigItem(
                        key=item["key"],
                        item_type=item.get("type", "numeric"),
                        interval=item.get("interval", 60),
                        parameters=item.get("parameters", {})
                    )
                    for item in data.get("items", [])
                ]
                self.last_updated = data.get("updated_at")
                
                logger.info(f"Config updated: {len(self.items)} items")
                return True
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching config: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error fetching config: {e}")
            return False
    
    async def sync_loop(self, interval: int = 300):
        """Periodically sync configuration.
        
        Args:
            interval: Seconds between sync attempts (default 5 minutes)
        """
        import asyncio
        
        while True:
            await self.fetch_config()
            await asyncio.sleep(interval)
    
    def get_items_by_interval(self, target_interval: int) -> List[ConfigItem]:
        """Get items that should be collected at the given interval."""
        return [item for item in self.items if item.interval == target_interval]
    
    def get_all_keys(self) -> List[str]:
        """Get all metric keys to collect."""
        return [item.key for item in self.items]
