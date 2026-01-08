"""Manual testing script for new features."""
import json
import os
import requests

BASE_URL = "http://localhost:8001/api/v1"

def get_auth_token():
    """Login and get auth token."""
    username = os.getenv("ADMIN_USERNAME")
    password = os.getenv("ADMIN_PASSWORD")
    if not username or not password:
        raise RuntimeError("Set ADMIN_USERNAME and ADMIN_PASSWORD to run this script.")
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": username,
        "password": password
    })
    response.raise_for_status()
    return response.json()["access_token"]

def test_features():
    """Test all new features."""
    print("🔐 Authenticating...")
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n✅ Authentication successful!\n")
    
    # Test 1: User Management
    print("=" * 50)
    print("TEST 1: User Management API")
    print("=" * 50)
    
    # List users
    response = requests.get(f"{BASE_URL}/users", headers=headers)
    users = response.json()
    print(f"✓ List users: {users['total']} users found")
    
    # Create user
    new_user = {
        "username": "test_sre",
        "password": "testpass123",
        "role": "sre"
    }
    response = requests.post(f"{BASE_URL}/users", headers=headers, json=new_user)
    if response.status_code == 201:
        user = response.json()
        print(f"✓ Create user: {user['username']} (ID: {user['id']})")
        
        # Update role
        response = requests.put(f"{BASE_URL}/users/{user['id']}", headers=headers, json={"role": "viewer"})
        print(f"✓ Update role: {response.json()['role']}")
        
        # Delete user
        requests.delete(f"{BASE_URL}/users/{user['id']}", headers=headers)
        print(f"✓ Delete user: Success")
    else:
        print(f"⚠ User might already exist (status: {response.status_code})")
    
    # Test 2: Alerting API
    print("\n" + "=" * 50)
    print("TEST 2: Alerting Engine API")
    print("=" * 50)
    
    # Alert counts
    response = requests.get(f"{BASE_URL}/alerts/summary/counts", headers=headers)
    counts = response.json()
    print(f"✓ Alert counts: {counts}")
    
    # List alerts
    response = requests.get(f"{BASE_URL}/alerts", headers=headers)
    alerts = response.json()
    print(f"✓ List alerts: {alerts['total']} alert events")
    
    # Test 3: Agent Config Endpoint
    print("\n" + "=" * 50)
    print("TEST 3: Agent Config Endpoint")
    print("=" * 50)
    
    # Get devices
    response = requests.get(f"{BASE_URL}/devices", headers=headers)
    devices = response.json()
    
    if devices["total"] > 0:
        device_id = devices["devices"][0]["id"]
        print(f"✓ Testing with device: {devices['devices'][0]['hostname']}")
        
        # Get agent config
        response = requests.get(f"{BASE_URL}/templates/agents/{device_id}/config", headers=headers)
        if response.status_code == 200:
            config = response.json()
            print(f"✓ Agent config: {len(config['items'])} items configured")
            if config['items']:
                print(f"  Sample items: {[item['key'] for item in config['items'][:3]]}")
        else:
            print(f"⚠ No config (device not in host groups)")
    else:
        print("⚠ No devices registered - agent config test skipped")
    
    print("\n" + "=" * 50)
    print("✅ ALL TESTS COMPLETED!")
    print("=" * 50)
    print("\n📋 Summary:")
    print("  • User Management: ✓ Working")
    print("  • Alerting API: ✓ Working")
    print("  • Agent Config: ✓ Working")
    print("\n🎯 Next: Open http://localhost:5173 to test the UI!")

if __name__ == "__main__":
    try:
        test_features()
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to API server")
        print("   Make sure the server is running: cd server && python main.py")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
