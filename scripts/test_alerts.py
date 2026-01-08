# Alert Testing Script

import os
import requests
import time
import psutil

def trigger_cpu_alert():
    """Simulate high CPU usage"""
    print("🔥 Triggering CPU alert...")
    print("Starting CPU stress test (30 seconds)...")
    
    end_time = time.time() + 30
    while time.time() < end_time:
        # CPU intensive operation
        [x**2 for x in range(10000)]
    
    print("✅ CPU stress test complete")
    print("Alert should fire if CPU > 80-90% for 5 minutes")

def trigger_memory_alert():
    """Simulate high memory usage"""
    print("\n💾 Triggering memory alert...")
    print("Allocating large arrays...")
    
    # Allocate ~1GB of memory
    data = []
    for i in range(10):
        data.append(bytearray(100 * 1024 * 1024))  # 100MB chunks
        print(f"Allocated {(i+1) * 100}MB")
        time.sleep(1)
    
    print("✅ Memory allocated")
    print("Alert should fire if memory > 85% for 5 minutes")
    
    input("Press Enter to release memory and continue...")
    data.clear()

def test_webhook():
    """Test alert webhook endpoint"""
    print("\n📡 Testing webhook endpoint...")
    
    payload = {
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "Test Alert",
                    "severity": "warning",
                    "host_name": "test-device"
                },
                "annotations": {
                    "summary": "This is a test alert",
                    "description": "Testing webhook integration"
                }
            }
        ]
    }
    
    webhook_url = os.getenv("ALERT_WEBHOOK_URL", "http://localhost:8001/api/v1/alerts/webhook")
    webhook_token = os.getenv("ALERT_WEBHOOK_TOKEN")
    if not webhook_token:
        print("❌ ALERT_WEBHOOK_TOKEN is not set. Export it before running this test.")
        return
    webhook_url = f"{webhook_url}?token={webhook_token}"

    try:
        response = requests.post(webhook_url, json=payload, timeout=5)
        print(f"✅ Webhook response: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"❌ Webhook test failed: {e}")

def check_system_status():
    """Display current system metrics"""
    print("\n📊 Current System Status:")
    print(f"CPU: {psutil.cpu_percent(interval=1)}%")
    print(f"Memory: {psutil.virtual_memory().percent}%")
    print(f"Disk: {psutil.disk_usage('/').percent}%")

if __name__ == "__main__":
    print("🚨 Health Monitor - Alert Testing Tool\n")
    print("=" * 50)
    
    check_system_status()
    
    print("\n" + "=" * 50)
    print("Select test:")
    print("1. Trigger CPU alert")
    print("2. Trigger memory alert")
    print("3. Test webhook endpoint")
    print("4. Show current metrics")
    print("0. Exit")
    
    choice = input("\nEnter choice: ")
    
    if choice == "1":
        trigger_cpu_alert()
    elif choice == "2":
        trigger_memory_alert()
    elif choice == "3":
        test_webhook()
    elif choice == "4":
        check_system_status()
    else:
        print("Exiting...")
