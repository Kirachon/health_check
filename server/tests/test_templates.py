"""Tests for Templates API endpoints."""
import pytest
from uuid import uuid4


class TestTemplatesAPI:
    """Tests for /api/v1/templates endpoints."""

    def test_create_template_success(self, authenticated_client):
        """Test creating a new template."""
        response = authenticated_client.post(
            "/api/v1/templates",
            json={"name": "Linux by Zabbix Agent", "description": "Template for Linux hosts", "template_type": "agent"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Linux by Zabbix Agent"
        assert data["description"] == "Template for Linux hosts"
        assert data["template_type"] == "agent"
        assert data["item_count"] == 0
        assert data["trigger_count"] == 0
        assert "id" in data

    def test_create_template_duplicate_name(self, authenticated_client):
        """Test creating a template with a duplicate name fails."""
        authenticated_client.post(
            "/api/v1/templates",
            json={"name": "Duplicate Template"}
        )
        response = authenticated_client.post(
            "/api/v1/templates",
            json={"name": "Duplicate Template"}
        )
        assert response.status_code == 409

    def test_list_templates_empty(self, authenticated_client):
        """Test listing templates when empty."""
        response = authenticated_client.get("/api/v1/templates")
        assert response.status_code == 200
        data = response.json()
        assert data["templates"] == []
        assert data["total"] == 0

    def test_list_templates_with_data(self, authenticated_client):
        """Test listing templates with data."""
        authenticated_client.post("/api/v1/templates", json={"name": "Template A"})
        authenticated_client.post("/api/v1/templates", json={"name": "Template B"})

        response = authenticated_client.get("/api/v1/templates")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_list_templates_with_search(self, authenticated_client):
        """Test searching templates by name."""
        authenticated_client.post("/api/v1/templates", json={"name": "Linux Agent"})
        authenticated_client.post("/api/v1/templates", json={"name": "Windows Agent"})
        authenticated_client.post("/api/v1/templates", json={"name": "SNMP Generic"})

        response = authenticated_client.get("/api/v1/templates?search=Agent")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_list_templates_filter_type(self, authenticated_client):
        """Test filtering templates by type."""
        authenticated_client.post("/api/v1/templates", json={"name": "Agent Template", "template_type": "agent"})
        authenticated_client.post("/api/v1/templates", json={"name": "SNMP Template", "template_type": "snmp"})

        response = authenticated_client.get("/api/v1/templates?template_type=agent")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["templates"][0]["template_type"] == "agent"

    def test_get_template_success(self, authenticated_client):
        """Test getting a specific template by ID."""
        create_resp = authenticated_client.post(
            "/api/v1/templates",
            json={"name": "Test Get Template", "description": "Test description"}
        )
        template_id = create_resp.json()["id"]

        response = authenticated_client.get(f"/api/v1/templates/{template_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == template_id
        assert data["name"] == "Test Get Template"
        assert "items" in data  # Detail response includes items

    def test_get_template_not_found(self, authenticated_client):
        """Test getting a non-existent template."""
        fake_id = uuid4()
        response = authenticated_client.get(f"/api/v1/templates/{fake_id}")
        assert response.status_code == 404

    def test_update_template_success(self, authenticated_client):
        """Test updating a template."""
        create_resp = authenticated_client.post(
            "/api/v1/templates",
            json={"name": "Original", "description": "Original desc"}
        )
        template_id = create_resp.json()["id"]

        response = authenticated_client.put(
            f"/api/v1/templates/{template_id}",
            json={"name": "Updated", "description": "Updated desc"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated"
        assert data["description"] == "Updated desc"

    def test_delete_template_success(self, authenticated_client):
        """Test deleting a template."""
        create_resp = authenticated_client.post(
            "/api/v1/templates",
            json={"name": "To Delete"}
        )
        template_id = create_resp.json()["id"]

        response = authenticated_client.delete(f"/api/v1/templates/{template_id}")
        assert response.status_code == 204

        # Verify it's gone
        response = authenticated_client.get(f"/api/v1/templates/{template_id}")
        assert response.status_code == 404


class TestTemplateItemsAPI:
    """Tests for template items endpoints."""

    def test_create_template_item_success(self, authenticated_client):
        """Test adding an item to a template."""
        # Create template first
        create_resp = authenticated_client.post(
            "/api/v1/templates",
            json={"name": "Template With Items"}
        )
        template_id = create_resp.json()["id"]

        # Add item
        response = authenticated_client.post(
            f"/api/v1/templates/{template_id}/items",
            json={
                "name": "CPU Load",
                "key": "system.cpu.load[avg1]",
                "value_type": "numeric",
                "units": "%",
                "update_interval": 60
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "CPU Load"
        assert data["key"] == "system.cpu.load[avg1]"
        assert data["units"] == "%"

    def test_create_template_item_duplicate_key(self, authenticated_client):
        """Test adding an item with duplicate key fails."""
        # Create template
        create_resp = authenticated_client.post(
            "/api/v1/templates",
            json={"name": "Duplicate Key Test"}
        )
        template_id = create_resp.json()["id"]

        # Add first item
        authenticated_client.post(
            f"/api/v1/templates/{template_id}/items",
            json={"name": "CPU Load", "key": "system.cpu.load"}
        )

        # Try to add duplicate
        response = authenticated_client.post(
            f"/api/v1/templates/{template_id}/items",
            json={"name": "Another CPU Load", "key": "system.cpu.load"}
        )
        assert response.status_code == 409

    def test_template_item_count_updates(self, authenticated_client):
        """Test that item_count is updated when items are added."""
        # Create template
        create_resp = authenticated_client.post(
            "/api/v1/templates",
            json={"name": "Count Test"}
        )
        template_id = create_resp.json()["id"]

        # Add items
        authenticated_client.post(
            f"/api/v1/templates/{template_id}/items",
            json={"name": "Item 1", "key": "key1"}
        )
        authenticated_client.post(
            f"/api/v1/templates/{template_id}/items",
            json={"name": "Item 2", "key": "key2"}
        )

        # Check template
        response = authenticated_client.get(f"/api/v1/templates/{template_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["item_count"] == 2
        assert len(data["items"]) == 2

    def test_delete_template_item_success(self, authenticated_client):
        """Test deleting an item from a template."""
        # Create template
        create_resp = authenticated_client.post(
            "/api/v1/templates",
            json={"name": "Delete Item Test"}
        )
        template_id = create_resp.json()["id"]

        # Add item
        item_resp = authenticated_client.post(
            f"/api/v1/templates/{template_id}/items",
            json={"name": "To Delete", "key": "delete.key"}
        )
        item_id = item_resp.json()["id"]

        # Delete item
        response = authenticated_client.delete(f"/api/v1/templates/{template_id}/items/{item_id}")
        assert response.status_code == 204

        # Verify template shows 0 items
        template_resp = authenticated_client.get(f"/api/v1/templates/{template_id}")
        assert template_resp.json()["item_count"] == 0

    def test_delete_template_item_not_found(self, authenticated_client):
        """Test deleting a non-existent item."""
        # Create template
        create_resp = authenticated_client.post(
            "/api/v1/templates",
            json={"name": "Item Not Found Test"}
        )
        template_id = create_resp.json()["id"]
        fake_item_id = uuid4()

        response = authenticated_client.delete(f"/api/v1/templates/{template_id}/items/{fake_item_id}")
        assert response.status_code == 404
