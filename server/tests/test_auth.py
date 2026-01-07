def test_login_success(client):
    """Test successful login"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client):
    """Test login with wrong password"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrongpassword"}
    )
    
    assert response.status_code == 401


def test_refresh_token(client):
    """Test token refresh"""
    # Login
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    tokens = login_response.json()
    
    # Refresh
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]}
    )
    
    assert response.status_code == 200
    new_tokens = response.json()
    assert "access_token" in new_tokens
    assert new_tokens["access_token"] != tokens["access_token"]


def test_logout(client):
    """Test logout revokes refresh token"""
    # Login
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    tokens = login_response.json()
    
    # Logout
    response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]}
    )
    
    assert response.status_code == 200
    
    # Try to use refresh token again (should fail)
    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]}
    )
    
    assert refresh_response.status_code == 401


def test_protected_endpoint_without_token(client):
    """Test accessing protected endpoint without token"""
    response = client.get("/api/v1/devices")
    assert response.status_code == 403  # Missing auth header


def test_protected_endpoint_with_invalid_token(client):
    """Test accessing protected endpoint with invalid token"""
    client.headers = {"Authorization": "Bearer invalid_token"}
    response = client.get("/api/v1/devices")
    assert response.status_code == 401
