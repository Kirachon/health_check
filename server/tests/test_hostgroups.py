"""Tests for Host Groups API endpoints."""
import pytest
from uuid import uuid4


class TestHostGroupsAPI:
    """Tests for /api/v1/hostgroups endpoints."""

    def test_create_hostgroup_success(self, authenticated_client):
        """Test creating a new host group."""
        response = authenticated_client.post(
            "/api/v1/hostgroups",
            json={"name": "Production Servers", "description": "All production server hosts"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Production Servers"
        assert data["description"] == "All production server hosts"
        assert data["device_count"] == 0
        assert data["template_count"] == 0
        assert "id" in data

    def test_create_hostgroup_duplicate_name(self, authenticated_client):
        """Test creating a host group with a duplicate name fails."""
        # Create first group
        authenticated_client.post(
            "/api/v1/hostgroups",
            json={"name": "Duplicate Test", "description": "First one"}
        )
        # Try to create duplicate
        response = authenticated_client.post(
            "/api/v1/hostgroups",
            json={"name": "Duplicate Test", "description": "Second one"}
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_create_hostgroup_unauthenticated(self, client):
        """Test that unauthenticated requests are rejected."""
        response = client.post(
            "/api/v1/hostgroups",
            json={"name": "Unauthorized Group"}
        )
        # FastAPI's OAuth2 dependency returns 403 when no token is provided
        assert response.status_code == 403

    def test_list_hostgroups_empty(self, authenticated_client):
        """Test listing host groups when empty."""
        response = authenticated_client.get("/api/v1/hostgroups")
        assert response.status_code == 200
        data = response.json()
        assert data["host_groups"] == []
        assert data["total"] == 0

    def test_list_hostgroups_with_data(self, authenticated_client):
        """Test listing host groups with data."""
        # Create some groups
        authenticated_client.post("/api/v1/hostgroups", json={"name": "Group A"})
        authenticated_client.post("/api/v1/hostgroups", json={"name": "Group B"})
        authenticated_client.post("/api/v1/hostgroups", json={"name": "Group C"})

        response = authenticated_client.get("/api/v1/hostgroups")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["host_groups"]) == 3

    def test_list_hostgroups_with_search(self, authenticated_client):
        """Test searching host groups by name."""
        authenticated_client.post("/api/v1/hostgroups", json={"name": "Linux Production"})
        authenticated_client.post("/api/v1/hostgroups", json={"name": "Windows Servers"})
        authenticated_client.post("/api/v1/hostgroups", json={"name": "Linux Dev"})

        response = authenticated_client.get("/api/v1/hostgroups?search=Linux")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        names = [hg["name"] for hg in data["host_groups"]]
        assert "Linux Production" in names
        assert "Linux Dev" in names

    def test_get_hostgroup_success(self, authenticated_client):
        """Test getting a specific host group by ID."""
        # Create a group
        create_resp = authenticated_client.post(
            "/api/v1/hostgroups",
            json={"name": "Test Get", "description": "Test description"}
        )
        hg_id = create_resp.json()["id"]

        # Fetch it
        response = authenticated_client.get(f"/api/v1/hostgroups/{hg_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == hg_id
        assert data["name"] == "Test Get"

    def test_get_hostgroup_not_found(self, authenticated_client):
        """Test getting a non-existent host group."""
        fake_id = uuid4()
        response = authenticated_client.get(f"/api/v1/hostgroups/{fake_id}")
        assert response.status_code == 404

    def test_update_hostgroup_success(self, authenticated_client):
        """Test updating a host group."""
        # Create a group
        create_resp = authenticated_client.post(
            "/api/v1/hostgroups",
            json={"name": "Original Name", "description": "Original description"}
        )
        hg_id = create_resp.json()["id"]

        # Update it
        response = authenticated_client.put(
            f"/api/v1/hostgroups/{hg_id}",
            json={"name": "New Name", "description": "New description"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["description"] == "New description"

    def test_update_hostgroup_not_found(self, authenticated_client):
        """Test updating a non-existent host group."""
        fake_id = uuid4()
        response = authenticated_client.put(
            f"/api/v1/hostgroups/{fake_id}",
            json={"name": "Updated Name"}
        )
        assert response.status_code == 404

    def test_delete_hostgroup_success(self, authenticated_client):
        """Test deleting a host group."""
        # Create a group
        create_resp = authenticated_client.post(
            "/api/v1/hostgroups",
            json={"name": "To Delete"}
        )
        hg_id = create_resp.json()["id"]

        # Delete it
        response = authenticated_client.delete(f"/api/v1/hostgroups/{hg_id}")
        assert response.status_code == 204

        # Verify it's gone
        response = authenticated_client.get(f"/api/v1/hostgroups/{hg_id}")
        assert response.status_code == 404

    def test_delete_hostgroup_not_found(self, authenticated_client):
        """Test deleting a non-existent host group."""
        fake_id = uuid4()
        response = authenticated_client.delete(f"/api/v1/hostgroups/{fake_id}")
        assert response.status_code == 404
