import pytest
from unittest.mock import Mock, patch
from collector import MetricsCollector


def test_get_device_info():
    """Test device info collection"""
    collector = MetricsCollector()
    info = collector.get_device_info()
    
    assert "hostname" in info
    assert "ip" in info
    assert "os" in info
    assert len(info["hostname"]) > 0
    assert len(info["os"]) > 0


def test_collect_cpu_metrics():
    """Test CPU metrics collection"""
    collector = MetricsCollector()
    metrics = collector.collect_cpu_metrics()
    
    assert "cpu_percent" in metrics
    assert "cpu_count" in metrics
    assert 0 <= metrics["cpu_percent"] <= 100
    assert metrics["cpu_count"] > 0


def test_collect_memory_metrics():
    """Test memory metrics collection"""
    collector = MetricsCollector()
    metrics = collector.collect_memory_metrics()
    
    assert "memory_percent" in metrics
    assert "memory_total_gb" in metrics
    assert "memory_used_gb" in metrics
    assert 0 <= metrics["memory_percent"] <= 100
    assert metrics["memory_total_gb"] > 0


def test_collect_disk_metrics():
    """Test disk metrics collection"""
    collector = MetricsCollector()
    metrics = collector.collect_disk_metrics()
    
    # Should have at least one disk partition
    assert len(metrics) > 0
    
    # Check for expected metric patterns
    has_percent = any("disk_percent" in k for k in metrics.keys())
    assert has_percent


def test_collect_network_metrics():
    """Test network metrics collection"""
    collector = MetricsCollector()
    metrics = collector.collect_network_metrics()
    
    assert "network_bytes_sent" in metrics
    assert "network_bytes_recv" in metrics
    assert "network_send_rate_mbps" in metrics
    assert metrics["network_bytes_sent"] >= 0
    assert metrics["network_bytes_recv"] >= 0


def test_collect_all_metrics():
    """Test collecting all metrics"""
    collector = MetricsCollector()
    config = {
        "cpu": True,
        "memory": True,
        "disk": True,
        "network": True
    }
    
    metrics = collector.collect_all_metrics(config)
    
    # Should have metrics from all categories
    assert "cpu_percent" in metrics
    assert "memory_percent" in metrics
    assert "network_bytes_sent" in metrics
    assert len(metrics) > 10  # Should have many metrics


def test_collect_selective_metrics():
    """Test collecting only selected metrics"""
    collector = MetricsCollector()
    config = {
        "cpu": True,
        "memory": False,
        "disk": False,
        "network": False
    }
    
    metrics = collector.collect_all_metrics(config)
    
    # Should only have CPU metrics
    assert "cpu_percent" in metrics
    assert "memory_percent" not in metrics
    assert "network_bytes_sent" not in metrics
