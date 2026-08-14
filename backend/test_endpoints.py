import requests
import json
from datetime import datetime
import os

BASE_URL = "http://localhost:8000"
API_KEY = os.environ.get("UEBA_API_KEY", "dev-local-key")
HEADERS = {"X-API-Key": API_KEY}

def print_section(title):
    print(f"\n{'='*50}")
    print(f"{title}")
    print(f"{'='*50}")

def print_response(response):
    print(f"Status Code: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2))
    except Exception:
        print(response.text)

def main():
    print_section("1. Testing GET /health")
    try:
        res = requests.get(f"{BASE_URL}/health")
        print_response(res)
    except Exception as e:
        print(f"Error: {e}")

    print_section("2. Testing GET /alerts")
    try:
        res = requests.get(f"{BASE_URL}/alerts", headers=HEADERS)
        if res.status_code == 200:
            alerts = res.json()
            print(f"Status Code: 200")
            print(f"Returned {len(alerts)} alerts. Showing first 3 for brevity:")
            print(json.dumps(alerts[:3], indent=2))
        else:
            print_response(res)
    except Exception as e:
        print(f"Error: {e}")

    print_section("3. Testing GET /alerts/summary")
    try:
        res = requests.get(f"{BASE_URL}/alerts/summary", headers=HEADERS)
        print_response(res)
    except Exception as e:
        print(f"Error: {e}")

    print_section("4. Testing GET /user/U001")
    try:
        res = requests.get(f"{BASE_URL}/user/U001", headers=HEADERS)
        if res.status_code == 200:
            data = res.json()
            print(f"Status Code: 200")
            print(f"Baseline (Keys): {list(data.get('baseline', {}).keys())}")
            print(f"Activity History (Count): {len(data.get('activity_history', []))}")
            print(f"Risk History (Count): {len(data.get('risk_history', []))}")
            print("\nBaseline snippet:")
            print(json.dumps(data.get('baseline'), indent=2))
        else:
            print_response(res)
    except Exception as e:
        print(f"Error: {e}")

    print_section("5. Testing POST /simulate-event")
    payload = {
        "user_id": "U001",
        "timestamp": datetime.now().isoformat(),
        "login_hour": 3,
        "location": "Remote Island",
        "ip_address": "8.8.8.8",
        "device_id": "unknown_device_x",
        "download_mb": 9500.5,
        "files_accessed": 500,
        "accessed_department": "Engineering" # using a real looking dept to trigger mismatch if U001 is not engineering (U001 is HR usually)
    }
    try:
        print(f"Sending payload:\n{json.dumps(payload, indent=2)}")
        res = requests.post(f"{BASE_URL}/simulate-event", json=payload, headers=HEADERS)
        print("\nResponse:")
        print_response(res)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
