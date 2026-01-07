"""Tests for Triggers API endpoints."""
import pytest
from uuid import uuid4


class TestTriggersAPI:
    """Tests for /api/v1/triggers endpoints."""

    def test_create_trigger_success(self, authenticated_client):
        """Test creating a new trigger."""
        response = authenticated_client.post(
            "/api/v1/triggers",
            json={
                "name": "High CPU Usage on {HOST.NAME}",
                "expression": "{Linux:cpu.load.avg(5m)}>80",
                "severity": "high",
                "description": "Trigger when CPU is above 80%"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "High CPU Usage on {HOST.NAME}"
        assert data["expression"] == "{Linux:cpu.load.avg(5m)}>80"
        assert data["severity"] == "high"
        assert data["enabled"] is True

    def test_create_trigger_invalid_severity(self, authenticated_client):
        """Test creating a trigger with invalid severity fails."""
        response = authenticated_client.post(
            "/api/v1/triggers",
            json={
                "name": "Test Trigger",
                "expression": "{host:metric}>0",
                "severity": "critical"  # Invalid - should be "disaster"
            }
        )
        assert response.status_code == 400
        assert "Invalid severity" in response.json()["detail"]

    def test_create_trigger_with_template(self, authenticated_client):
        """Test creating a trigger linked to a template."""
        # Create template first
        template_resp = authenticated_client.post(
            "/api/v1/templates",
            json={"name": "Linux Template"}
        )
        template_id = template_resp.json()["id"]

        # Create trigger linked to template
        response = authenticated_client.post(
            "/api/v1/triggers",
            json={
                "name": "Template Trigger",
                "expression": "{host:cpu}>90",
                "template_id": template_id
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["template_id"] == template_id
        assert data["template_name"] == "Linux Template"

    def test_create_trigger_nonexistent_template(self, authenticated_client):
        """Test creating a trigger with non-existent template fails."""
        fake_template_id = uuid4()
        response = authenticated_client.post(
            "/api/v1/triggers",
            json={
                "name": "Test Trigger",
                "expression": "{host:metric}>0",
                "template_id": str(fake_template_id)
            }
        )
        assert response.status_code == 404

    def test_list_triggers_empty(self, authenticated_client):
        """Test listing triggers when empty."""
        response = authenticated_client.get("/api/v1/triggers")
        assert response.status_code == 200
        data = response.json()
        assert data["triggers"] == []
        assert data["total"] == 0

    def test_list_triggers_with_data(self, authenticated_client):
        """Test listing triggers with data."""
        authenticated_client.post("/api/v1/triggers", json={"name": "Trigger A", "expression": "a>b"})
        authenticated_client.post("/api/v1/triggers", json={"name": "Trigger B", "expression": "c>d"})

        response = authenticated_client.get("/api/v1/triggers")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_list_triggers_filter_severity(self, authenticated_client):
        """Test filtering triggers by severity."""
        authenticated_client.post("/api/v1/triggers", json={"name": "High", "expression": "a>b", "severity": "high"})
        authenticated_client.post("/api/v1/triggers", json={"name": "Warning", "expression": "c>d", "severity": "warning"})

        response = authenticated_client.get("/api/v1/triggers?severity=high")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["triggers"][0]["severity"] == "high"

    def test_list_triggers_filter_enabled(self, authenticated_client):
        """Test filtering triggers by enabled status."""
        authenticated_client.post("/api/v1/triggers", json={"name": "Enabled", "expression": "a>b", "enabled": True})
        authenticated_client.post("/api/v1/triggers", json={"name": "Disabled", "expression": "c>d", "enabled": False})

        response = authenticated_client.get("/api/v1/triggers?enabled=true")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_get_trigger_success(self, authenticated_client):
        """Test getting a specific trigger by ID."""
        create_resp = authenticated_client.post(
            "/api/v1/triggers",
            json={"name": "Test Get", "expression": "x>y"}
        )
        trigger_id = create_resp.json()["id"]

        response = authenticated_client.get(f"/api/v1/triggers/{trigger_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == trigger_id
        assert data["name"] == "Test Get"

    def test_get_trigger_not_found(self, authenticated_client):
        """Test getting a non-existent trigger."""
        fake_id = uuid4()
        response = authenticated_client.get(f"/api/v1/triggers/{fake_id}")
        assert response.status_code == 404

    def test_update_trigger_success(self, authenticated_client):
        """Test updating a trigger."""
        create_resp = authenticated_client.post(
            "/api/v1/triggers",
            json={"name": "Original", "expression": "x>y", "severity": "warning"}
        )
        trigger_id = create_resp.json()["id"]

        response = authenticated_client.put(
            f"/api/v1/triggers/{trigger_id}",
            json={"name": "Updated", "severity": "disaster"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated"
        assert data["severity"] == "disaster"

    def test_update_trigger_invalid_severity(self, authenticated_client):
        """Test updating a trigger with invalid severity fails."""
        create_resp = authenticated_client.post(
            "/api/v1/triggers",
            json={"name": "Test", "expression": "x>y"}
        )
        trigger_id = create_resp.json()["id"]

        response = authenticated_client.put(
            f"/api/v1/triggers/{trigger_id}",
            json={"severity": "invalid"}
        )
        assert response.status_code == 400

    def test_delete_trigger_success(self, authenticated_client):
        """Test deleting a trigger."""
        create_resp = authenticated_client.post(
            "/api/v1/triggers",
            json={"name": "To Delete", "expression": "x>y"}
        )
        trigger_id = create_resp.json()["id"]

        response = authenticated_client.delete(f"/api/v1/triggers/{trigger_id}")
        assert response.status_code == 204

        # Verify it's gone
        response = authenticated_client.get(f"/api/v1/triggers/{trigger_id}")
        assert response.status_code == 404

    def test_toggle_trigger(self, authenticated_client):
        """Test toggling trigger enabled status."""
        create_resp = authenticated_client.post(
            "/api/v1/triggers",
            json={"name": "Toggle Test", "expression": "x>y", "enabled": True}
        )
        trigger_id = create_resp.json()["id"]
        assert create_resp.json()["enabled"] is True

        # Toggle off
        response = authenticated_client.post(f"/api/v1/triggers/{trigger_id}/toggle")
        assert response.status_code == 200
        assert response.json()["enabled"] is False

        # Toggle on
        response = authenticated_client.post(f"/api/v1/triggers/{trigger_id}/toggle")
        assert response.status_code == 200
        assert response.json()["enabled"] is True
