#!/usr/bin/env python3
import yaml
import time
import logging
import signal
import sys
from pathlib import Path
from typing import Dict
from urllib.parse import urlparse, urlunparse
import requests

from collector import MetricsCollector
from sender import MetricsSender


# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global shutdown_requested
    logging.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True


def load_config(config_path: str = "config.yaml") -> Dict:
    """Load configuration from YAML file"""
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logging.error(f"Config file not found: {config_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        logging.error(f"Invalid YAML in config file: {e}")
        sys.exit(1)


def register_device(config: Dict, device_info: Dict) -> Dict:
    """Register device with the server if not already registered"""
    # Check if already registered
    if config.get("device_id") and config.get("device_token"):
        logging.info(f"Device already registered with ID: {config['device_id']}")
        return config
    
    # Register new device
    server_api = get_api_v1_url(config)
    try:
        response = requests.post(
            f"{server_api}/devices/register",
            json=device_info,
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        device_id = data["device_id"]
        device_token = data["token"]
        
        logging.info(f"Device registered successfully. ID: {device_id}")
        
        # Update config file with credentials
        config["device_id"] = device_id
        config["device_token"] = device_token
        
        with open("config.yaml", "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        
        return config
        
    except requests.RequestException as e:
        logging.error(f"Failed to register device: {e}")
        logging.warning("Continuing without registration. Metrics may not be accepted.")
        return config


def send_heartbeat(config: Dict):
    """Send heartbeat to update device status"""
    if not config.get("device_id"):
        return
    
    server_api = get_api_v1_url(config)
    try:
        response = requests.post(
            f"{server_api}/devices/{config['device_id']}/heartbeat",
            timeout=5
        )
        response.raise_for_status()
    except requests.RequestException as e:
        logging.debug(f"Heartbeat failed: {e}")


def get_api_v1_url(config: Dict) -> str:
    """Return FastAPI base URL including /api/v1.

    Prefer explicit `api_url` in config. Otherwise infer from `server_url` host and
    assume FastAPI runs on port 8001 (project default).
    """
    api_url = (config.get("api_url") or "").strip()
    if api_url:
        api_url = api_url.rstrip("/")
        return api_url if api_url.endswith("/api/v1") else f"{api_url}/api/v1"

    server_url = (config.get("server_url") or "").strip().rstrip("/")
    if not server_url:
        # Safe default for local dev
        return "http://localhost:8001/api/v1"

    parsed = urlparse(server_url)
    hostname = parsed.hostname or "localhost"
    scheme = parsed.scheme or "http"

    # Default FastAPI port for this project
    netloc = f"{hostname}:8001"
    if parsed.username or parsed.password:
        auth = parsed.username or ""
        if parsed.password:
            auth = f"{auth}:{parsed.password}"
        netloc = f"{auth}@{netloc}"

    return urlunparse((scheme, netloc, "/api/v1", "", "", ""))


def main():
    """Main agent loop"""
    global shutdown_requested
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Load configuration
    config = load_config()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, config.get("log_level", "INFO")),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger(__name__)
    
    logger.info("Health Monitor Agent starting...")
    
    # Initialize collector
    collector = MetricsCollector()
    device_info = collector.get_device_info()
    
    # Override with config if provided
    if config.get("hostname"):
        device_info["hostname"] = config["hostname"]
    if config.get("ip"):
        device_info["ip"] = config["ip"]
    
    logger.info(f"Device: {device_info['hostname']} ({device_info['ip']})")
    
    # Register device (if needed)
    config = register_device(config, device_info)
    
    # Initialize sender
    sender = MetricsSender(config, device_info)
    
    # Main collection loop
    collection_interval = config.get("collection_interval", 30)
    logger.info(f"Starting metrics collection (interval: {collection_interval}s)")
    
    while not shutdown_requested:
        try:
            # Collect metrics
            metrics_data = collector.collect_all_metrics(config)
            logger.debug(f"Collected {len(metrics_data)} metrics")
            
            # Send metrics
            sender.send_with_retry(metrics_data)
            
            # Send heartbeat
            send_heartbeat(config)
            
            # Wait for next collection
            time.sleep(collection_interval)
            
        except Exception as e:
            logger.error(f"Error in collection loop: {e}", exc_info=True)
            time.sleep(5)  # Brief pause before retry
    
    # Graceful shutdown
    logger.info("Shutting down...")
    sender.shutdown()
    logger.info("Agent stopped")


if __name__ == "__main__":
    main()
