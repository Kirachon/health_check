"""Tests for Actions API endpoints."""
import pytest
from uuid import uuid4


class TestActionsAPI:
    """Tests for /api/v1/actions endpoints."""

    def test_create_action_success(self, authenticated_client):
        """Test creating a new action."""
        response = authenticated_client.post(
            "/api/v1/actions",
            json={
                "name": "Notify Admin on Disaster",
                "action_type": "notification",
                "conditions": '{"severity": "disaster"}'
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Notify Admin on Disaster"
        assert data["action_type"] == "notification"
        assert data["enabled"] is True
        assert data["operation_count"] == 0

    def test_create_action_invalid_type(self, authenticated_client):
        """Test creating an action with invalid type fails."""
        response = authenticated_client.post(
            "/api/v1/actions",
            json={"name": "Test", "action_type": "invalid_type"}
        )
        assert response.status_code == 400
        assert "Invalid action_type" in response.json()["detail"]

    def test_list_actions_empty(self, authenticated_client):
        """Test listing actions when empty."""
        response = authenticated_client.get("/api/v1/actions")
        assert response.status_code == 200
        data = response.json()
        assert data["actions"] == []
        assert data["total"] == 0

    def test_list_actions_with_data(self, authenticated_client):
        """Test listing actions with data."""
        authenticated_client.post("/api/v1/actions", json={"name": "Action A"})
        authenticated_client.post("/api/v1/actions", json={"name": "Action B"})

        response = authenticated_client.get("/api/v1/actions")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_list_actions_filter_type(self, authenticated_client):
        """Test filtering actions by type."""
        authenticated_client.post("/api/v1/actions", json={"name": "Notify", "action_type": "notification"})
        authenticated_client.post("/api/v1/actions", json={"name": "Script", "action_type": "script"})

        response = authenticated_client.get("/api/v1/actions?action_type=notification")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_get_action_success(self, authenticated_client):
        """Test getting a specific action by ID."""
        create_resp = authenticated_client.post(
            "/api/v1/actions",
            json={"name": "Test Get", "action_type": "remediation"}
        )
        action_id = create_resp.json()["id"]

        response = authenticated_client.get(f"/api/v1/actions/{action_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == action_id
        assert data["name"] == "Test Get"
        assert "operations" in data  # Detail response includes operations

    def test_get_action_not_found(self, authenticated_client):
        """Test getting a non-existent action."""
        fake_id = uuid4()
        response = authenticated_client.get(f"/api/v1/actions/{fake_id}")
        assert response.status_code == 404

    def test_update_action_success(self, authenticated_client):
        """Test updating an action."""
        create_resp = authenticated_client.post(
            "/api/v1/actions",
            json={"name": "Original", "action_type": "notification"}
        )
        action_id = create_resp.json()["id"]

        response = authenticated_client.put(
            f"/api/v1/actions/{action_id}",
            json={"name": "Updated", "action_type": "script"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated"
        assert data["action_type"] == "script"

    def test_delete_action_success(self, authenticated_client):
        """Test deleting an action."""
        create_resp = authenticated_client.post(
            "/api/v1/actions",
            json={"name": "To Delete"}
        )
        action_id = create_resp.json()["id"]

        response = authenticated_client.delete(f"/api/v1/actions/{action_id}")
        assert response.status_code == 204

        # Verify it's gone
        response = authenticated_client.get(f"/api/v1/actions/{action_id}")
        assert response.status_code == 404


class TestActionOperationsAPI:
    """Tests for action operations endpoints."""

    def test_create_action_operation_success(self, authenticated_client):
        """Test adding an operation to an action."""
        # Create action first
        create_resp = authenticated_client.post(
            "/api/v1/actions",
            json={"name": "Action With Operations"}
        )
        action_id = create_resp.json()["id"]

        # Add operation
        response = authenticated_client.post(
            f"/api/v1/actions/{action_id}/operations",
            json={
                "operation_type": "send_email",
                "parameters": '{"to": "admin@example.com", "subject": "Alert"}'
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["operation_type"] == "send_email"
        assert data["step_number"] == 1

    def test_create_operation_invalid_type(self, authenticated_client):
        """Test adding an operation with invalid type fails."""
        # Create action
        create_resp = authenticated_client.post(
            "/api/v1/actions",
            json={"name": "Test Action"}
        )
        action_id = create_resp.json()["id"]

        response = authenticated_client.post(
            f"/api/v1/actions/{action_id}/operations",
            json={"operation_type": "invalid"}
        )
        assert response.status_code == 400

    def test_operation_count_updates(self, authenticated_client):
        """Test that operation_count is updated when operations are added."""
        # Create action
        create_resp = authenticated_client.post(
            "/api/v1/actions",
            json={"name": "Count Test"}
        )
        action_id = create_resp.json()["id"]

        # Add operations
        authenticated_client.post(
            f"/api/v1/actions/{action_id}/operations",
            json={"operation_type": "send_email"}
        )
        authenticated_client.post(
            f"/api/v1/actions/{action_id}/operations",
            json={"operation_type": "send_telegram"}
        )

        # Check action
        response = authenticated_client.get(f"/api/v1/actions/{action_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["operation_count"] == 2
        assert len(data["operations"]) == 2

    def test_delete_action_operation_success(self, authenticated_client):
        """Test deleting an operation from an action."""
        # Create action
        create_resp = authenticated_client.post(
            "/api/v1/actions",
            json={"name": "Delete Op Test"}
        )
        action_id = create_resp.json()["id"]

        # Add operation
        op_resp = authenticated_client.post(
            f"/api/v1/actions/{action_id}/operations",
            json={"operation_type": "webhook"}
        )
        op_id = op_resp.json()["id"]

        # Delete operation
        response = authenticated_client.delete(f"/api/v1/actions/{action_id}/operations/{op_id}")
        assert response.status_code == 204

        # Verify action shows 0 operations
        action_resp = authenticated_client.get(f"/api/v1/actions/{action_id}")
        assert action_resp.json()["operation_count"] == 0

    def test_delete_action_cascades_operations(self, authenticated_client):
        """Test that deleting an action also deletes its operations."""
        # Create action
        create_resp = authenticated_client.post(
            "/api/v1/actions",
            json={"name": "Cascade Test"}
        )
        action_id = create_resp.json()["id"]

        # Add operation
        authenticated_client.post(
            f"/api/v1/actions/{action_id}/operations",
            json={"operation_type": "send_email"}
        )

        # Delete action
        response = authenticated_client.delete(f"/api/v1/actions/{action_id}")
        assert response.status_code == 204

        # Verify action is gone
        response = authenticated_client.get(f"/api/v1/actions/{action_id}")
        assert response.status_code == 404
