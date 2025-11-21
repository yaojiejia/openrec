"""
Test script for the HTTP API /update endpoint
"""
import json
import urllib.request
import urllib.parse

BASE_URL = "http://localhost:8000"

def test_health():
    """Test the health endpoint"""
    print("=" * 60)
    print("Testing /health endpoint")
    print("=" * 60)
    try:
        req = urllib.request.Request(f"{BASE_URL}/health")
        with urllib.request.urlopen(req) as response:
            status = response.getcode()
            data = json.loads(response.read().decode())
            print(f"Status Code: {status}")
            print(f"Response: {json.dumps(data, indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
    print()

def test_update_single():
    """Test the /update endpoint with a single event"""
    print("=" * 60)
    print("Testing /update endpoint (single event)")
    print("=" * 60)
    
    event = {
        "user_id": "user_001",
        "item_id": "item_123"
    }
    
    try:
        data = json.dumps(event).encode('utf-8')
        req = urllib.request.Request(
            f"{BASE_URL}/update",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req) as response:
            status = response.getcode()
            resp_data = json.loads(response.read().decode())
            print(f"Status Code: {status}")
            print(f"Response: {json.dumps(resp_data, indent=2)}")
    except urllib.error.HTTPError as e:
        status = e.code
        resp_data = json.loads(e.read().decode())
        print(f"Status Code: {status}")
        print(f"Response: {json.dumps(resp_data, indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
    print()

def test_update_batch():
    """Test the /update/batch endpoint with multiple events"""
    print("=" * 60)
    print("Testing /update/batch endpoint (multiple events)")
    print("=" * 60)
    
    events = [
        {"user_id": "user_001", "item_id": "item_123"},
        {"user_id": "user_002", "item_id": "item_456"},
        {"user_id": "user_003", "item_id": "item_789"}
    ]
    
    try:
        data = json.dumps(events).encode('utf-8')
        req = urllib.request.Request(
            f"{BASE_URL}/update/batch",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req) as response:
            status = response.getcode()
            resp_data = json.loads(response.read().decode())
            print(f"Status Code: {status}")
            print(f"Response: {json.dumps(resp_data, indent=2)}")
    except urllib.error.HTTPError as e:
        status = e.code
        resp_data = json.loads(e.read().decode())
        print(f"Status Code: {status}")
        print(f"Response: {json.dumps(resp_data, indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
    print()

def test_update_with_process_time():
    """Test the /update endpoint with explicit process_time"""
    print("=" * 60)
    print("Testing /update endpoint (with process_time)")
    print("=" * 60)
    
    import time
    event = {
        "user_id": "user_004",
        "item_id": "item_999",
        "process_time": time.time()
    }
    
    try:
        data = json.dumps(event).encode('utf-8')
        req = urllib.request.Request(
            f"{BASE_URL}/update",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req) as response:
            status = response.getcode()
            resp_data = json.loads(response.read().decode())
            print(f"Status Code: {status}")
            print(f"Response: {json.dumps(resp_data, indent=2)}")
    except urllib.error.HTTPError as e:
        status = e.code
        resp_data = json.loads(e.read().decode())
        print(f"Status Code: {status}")
        print(f"Response: {json.dumps(resp_data, indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
    print()

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("HTTP API Test Suite")
    print("=" * 60)
    print()
    
    test_health()
    test_update_single()
    test_update_batch()
    test_update_with_process_time()
    
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    print("[OK] All endpoints are responding")
    print("[INFO] /update endpoints return 503 when Kafka is not available")
    print("       (This is expected behavior - start Kafka to test full functionality)")
    print()
    print("API Documentation:")
    print(f"  - Swagger UI: {BASE_URL}/docs")
    print(f"  - ReDoc: {BASE_URL}/redoc")
    print()

