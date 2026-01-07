import psutil
import socket
import platform
from typing import Dict
from datetime import datetime


class MetricsCollector:
    """Collect system metrics using psutil"""
    
    def __init__(self):
        self.hostname = socket.gethostname()
        self.os = f"{platform.system()} {platform.release()}"
        
        # Initialize network counters for delta calculation
        self._last_net_io = psutil.net_io_counters()
        self._last_measurement_time = datetime.now()
    
    def get_device_info(self) -> Dict[str, str]:
        """Get device identification information"""
        try:
            # Try to get primary IP address
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
        except Exception:
            ip = "127.0.0.1"
        
        return {
            "hostname": self.hostname,
            "ip": ip,
            "os": self.os
        }
    
    def collect_cpu_metrics(self) -> Dict[str, float]:
        """Collect CPU metrics"""
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "cpu_count": psutil.cpu_count(),
            "cpu_freq_mhz": psutil.cpu_freq().current if psutil.cpu_freq() else 0.0
        }
    
    def collect_memory_metrics(self) -> Dict[str, float]:
        """Collect memory metrics"""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            "memory_percent": mem.percent,
            "memory_total_gb": mem.total / (1024 ** 3),
            "memory_available_gb": mem.available / (1024 ** 3),
            "memory_used_gb": mem.used / (1024 ** 3),
            "swap_percent": swap.percent,
            "swap_total_gb": swap.total / (1024 ** 3),
            "swap_used_gb": swap.used / (1024 ** 3)
        }
    
    def collect_disk_metrics(self) -> Dict[str, float]:
        """Collect disk metrics for all partitions"""
        metrics = {}
        
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                mount_clean = partition.mountpoint.replace(":", "").replace("\\", "_").replace("/", "_")
                
                metrics[f"disk_percent_{mount_clean}"] = usage.percent
                metrics[f"disk_total_gb_{mount_clean}"] = usage.total / (1024 ** 3)
                metrics[f"disk_used_gb_{mount_clean}"] = usage.used / (1024 ** 3)
                metrics[f"disk_free_gb_{mount_clean}"] = usage.free / (1024 ** 3)
            except (PermissionError, OSError):
                # Skip partitions we can't access
                continue
        
        # Disk I/O
        disk_io = psutil.disk_io_counters()
        if disk_io:
            metrics["disk_read_mb"] = disk_io.read_bytes / (1024 ** 2)
            metrics["disk_write_mb"] = disk_io.write_bytes / (1024 ** 2)
        
        return metrics
    
    def collect_network_metrics(self) -> Dict[str, float]:
        """Collect network metrics"""
        net_io = psutil.net_io_counters()
        now = datetime.now()
        
        # Calculate rates (bytes per second)
        time_delta = (now - self._last_measurement_time).total_seconds()
        if time_delta > 0:
            bytes_sent_rate = (net_io.bytes_sent - self._last_net_io.bytes_sent) / time_delta
            bytes_recv_rate = (net_io.bytes_recv - self._last_net_io.bytes_recv) / time_delta
        else:
            bytes_sent_rate = 0.0
            bytes_recv_rate = 0.0
        
        # Update last measurement
        self._last_net_io = net_io
        self._last_measurement_time = now
        
        return {
            "network_bytes_sent": net_io.bytes_sent,
            "network_bytes_recv": net_io.bytes_recv,
            "network_packets_sent": net_io.packets_sent,
            "network_packets_recv": net_io.packets_recv,
            "network_send_rate_mbps": bytes_sent_rate / (1024 ** 2),
            "network_recv_rate_mbps": bytes_recv_rate / (1024 ** 2)
        }
    
    def collect_all_metrics(self, config: Dict) -> Dict[str, float]:
        """Collect all enabled metrics"""
        metrics = {}
        
        if config.get("cpu", True):
            metrics.update(self.collect_cpu_metrics())
        
        if config.get("memory", True):
            metrics.update(self.collect_memory_metrics())
        
        if config.get("disk", True):
            metrics.update(self.collect_disk_metrics())
        
        if config.get("network", True):
            metrics.update(self.collect_network_metrics())
        
        return metrics
