def test_register_device(client):
    """Test device registration"""
    response = client.post(
        "/api/v1/devices/register",
        json={
            "hostname": "test-server",
            "ip": "192.168.1.100",
            "os": "Ubuntu 22.04"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "device_id" in data
    assert "token" in data
    assert data["token"].startswith("dev_")


def test_list_devices(authenticated_client):
    """Test listing devices (requires auth)"""
    # Register a device first
    device_response = authenticated_client.post(
        "/api/v1/devices/register",
        json={
            "hostname": "test-server",
            "ip": "192.168.1.100"
        }
    )
    assert device_response.status_code == 201
    
    # List devices
    response = authenticated_client.get("/api/v1/devices")
    
    assert response.status_code == 200
    data = response.json()
    assert "devices" in data
    assert "total" in data
    assert data["total"] >= 1


def test_get_device_details(authenticated_client):
    """Test getting device details"""
    # Register device
    register_response = authenticated_client.post(
        "/api/v1/devices/register",
        json={"hostname": "test-server", "ip": "192.168.1.100"}
    )
    device_id = register_response.json()["device_id"]
    
    # Get details
    response = authenticated_client.get(f"/api/v1/devices/{device_id}")
    
    assert response.status_code == 200
    device = response.json()
    assert device["hostname"] == "test-server"
    assert device["ip"] == "192.168.1.100"
    assert device["status"] == "offline"


def test_delete_device(authenticated_client):
    """Test device deletion"""
    # Register device
    register_response = authenticated_client.post(
        "/api/v1/devices/register",
        json={"hostname": "test-server", "ip": "192.168.1.100"}
    )
    device_id = register_response.json()["device_id"]
    
    # Delete
    response = authenticated_client.delete(f"/api/v1/devices/{device_id}")
    assert response.status_code == 204
    
    # Verify deleted
    get_response = authenticated_client.get(f"/api/v1/devices/{device_id}")
    assert get_response.status_code == 404


def test_filter_devices_by_status(authenticated_client):
    """Test filtering devices by status"""
    # Register devices
    authenticated_client.post(
        "/api/v1/devices/register",
        json={"hostname": "online-server", "ip": "192.168.1.101"}
    )
    authenticated_client.post(
        "/api/v1/devices/register",
        json={"hostname": "offline-server", "ip": "192.168.1.102"}
    )
    
    # Filter by offline status
    response = authenticated_client.get("/api/v1/devices?status=offline")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    for device in data["devices"]:
        assert device["status"] == "offline"
