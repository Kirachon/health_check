import pytest
from unittest.mock import Mock, patch, MagicMock
from sender import MetricsSender


@pytest.fixture
def mock_config():
    """Mock configuration"""
    return {
        "server_url": "http://localhost:8428",
        "device_id": "test-device-123",
        "device_token": "test-token",
        "collection_interval": 30,
        "retry_attempts": 3,
        "retry_delay": 1
    }


@pytest.fixture
def mock_device_info():
    """Mock device information"""
    return {
        "hostname": "test-host",
        "ip": "192.168.1.100",
        "os": "TestOS 1.0"
    }


def test_sender_initialization(mock_config, mock_device_info):
    """Test MetricsSender initialization"""
    with patch("sender.OTLPMetricExporter"):
        with patch("sender.PeriodicExportingMetricReader"):
            sender = MetricsSender(mock_config, mock_device_info)
            
            assert sender.config == mock_config
            assert sender.device_info == mock_device_info
            assert sender.meter is not None


def test_send_metrics_success(mock_config, mock_device_info):
    """Test successful metrics sending"""
    with patch("sender.OTLPMetricExporter"):
        with patch("sender.PeriodicExportingMetricReader"):
            sender = MetricsSender(mock_config, mock_device_info)
            
            metrics_data = {
                "cpu_percent": 25.5,
                "memory_percent": 60.2
            }
            
            # Mock the send operation
            with patch.object(sender, "send_metrics", return_value=True):
                result = sender.send_with_retry(metrics_data)
                assert result is True


def test_send_metrics_with_retry(mock_config, mock_device_info):
    """Test metrics sending with retry on failure"""
    mock_config["retry_delay"] = 0.1  # Speed up test
    
    with patch("sender.OTLPMetricExporter"):
        with patch("sender.PeriodicExportingMetricReader"):
            sender = MetricsSender(mock_config, mock_device_info)
            
            metrics_data = {"cpu_percent": 25.5}
            
            # Mock failure then success
            with patch.object(sender, "send_metrics", side_effect=[False, False, True]):
                result = sender.send_with_retry(metrics_data)
                assert result is True


def test_send_metrics_max_retries(mock_config, mock_device_info):
    """Test metrics sending fails after max retries"""
    mock_config["retry_delay"] = 0.1  # Speed up test
    
    with patch("sender.OTLPMetricExporter"):
        with patch("sender.PeriodicExportingMetricReader"):
            sender = MetricsSender(mock_config, mock_device_info)
            
            metrics_data = {"cpu_percent": 25.5}
            
            # Mock continuous failure
            with patch.object(sender, "send_metrics", return_value=False):
                result = sender.send_with_retry(metrics_data)
                assert result is False
