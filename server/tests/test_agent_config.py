"""Tests for agent config endpoint."""
import pytest
from fastapi.testclient import TestClient
from db.models import Device, HostGroup, Template, TemplateItem


class TestAgentConfig:
    """Test agent config endpoint."""

    def test_get_agent_config_device_not_found(self, authenticated_client: TestClient):
        """Test 404 for unknown device."""
        response = authenticated_client.get("/api/v1/templates/agents/00000000-0000-0000-0000-000000000000/config")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_agent_config_returns_empty_items(self, authenticated_client: TestClient, db):
        """Test config returns empty items for device without host groups."""
        from db.models import Device
        import hashlib
        
        # Create a device without any host groups
        device = Device(
            hostname="lonely-agent",
            ip="192.168.1.200",
            token_hash=hashlib.sha256(b"test-token-lonely").hexdigest()
        )
        db.add(device)
        db.commit()
        db.refresh(device)
        
        response = authenticated_client.get(f"/api/v1/templates/agents/{device.id}/config")
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data
        assert "device_id" in data
        assert len(data["items"]) == 0
