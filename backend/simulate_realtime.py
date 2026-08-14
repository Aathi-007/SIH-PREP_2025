"""
This script simulates real-time activity for the UEBA project demo.
IT IS MEANT TO BE RUN WHILE main.py (the FastAPI server) is already running 
in a separate terminal. It sends HTTP POST requests to the /simulate-event 
endpoint with a delay between each, simulating live incoming data.
"""

import requests
import time
from datetime import datetime
import json
import os

BASE_URL = "http://localhost:8000"
API_KEY = os.environ.get("UEBA_API_KEY", "dev-local-key")
HEADERS = {"X-API-Key": API_KEY}

def get_demo_events():
    """
    Returns a curated list of events for the demo.
    Mix of normal events (matching real users' usual patterns) and anomalous events.
    Order is normal first, then anomalies.
    """
    now = datetime.now().isoformat()
    
    events = [
        # --- NORMAL EVENTS ---
        {
            "user_id": "U001",
            "timestamp": now,
            "login_hour": 10,
            "location": "East Jill",
            "ip_address": "192.168.1.10",
            "device_id": "0822e8f3",
            "download_mb": 12.5,
            "files_accessed": 5,
            "accessed_department": "HR"
        },
        {
            "user_id": "U011",
            "timestamp": now,
            "login_hour": 11,
            "location": "East Nathaniel",
            "ip_address": "192.168.1.25",
            "device_id": "00257ad1",
            "download_mb": 35.0,
            "files_accessed": 8,
            "accessed_department": "Engineering"
        },
        {
            "user_id": "U001",
            "timestamp": now,
            "login_hour": 14,
            "location": "East Jill",
            "ip_address": "192.168.1.10",
            "device_id": "0822e8f3",
            "download_mb": 18.2,
            "files_accessed": 3,
            "accessed_department": "HR"
        },
        {
            "user_id": "U011",
            "timestamp": now,
            "login_hour": 15,
            "location": "East Nathaniel",
            "ip_address": "192.168.1.25",
            "device_id": "00257ad1",
            "download_mb": 42.1,
            "files_accessed": 12,
            "accessed_department": "Engineering"
        },
        {
            "user_id": "U001",
            "timestamp": now,
            "login_hour": 16,
            "location": "East Jill",
            "ip_address": "192.168.1.10",
            "device_id": "0822e8f3",
            "download_mb": 15.0,
            "files_accessed": 6,
            "accessed_department": "HR"
        },
        
        # --- ANOMALOUS EVENTS ---
        # 1. Massive download anomaly for U001 (Average is ~16MB)
        {
            "user_id": "U001",
            "timestamp": now,
            "login_hour": 11,
            "location": "East Jill",
            "ip_address": "192.168.1.10",
            "device_id": "0822e8f3",
            "download_mb": 4500.0,
            "files_accessed": 50,
            "accessed_department": "HR"
        },
        # 2. Login time and location anomaly for U011 (Usually 9-16, East Nathaniel)
        {
            "user_id": "U011",
            "timestamp": now,
            "login_hour": 3,
            "location": "Unknown Foreign City",
            "ip_address": "203.0.113.5",
            "device_id": "00257ad1",
            "download_mb": 10.0,
            "files_accessed": 2,
            "accessed_department": "Engineering"
        },
        # 3. Department mismatch and new device for U001 (Usually HR, device 0822e8f3)
        {
            "user_id": "U001",
            "timestamp": now,
            "login_hour": 13,
            "location": "East Jill",
            "ip_address": "192.168.1.10",
            "device_id": "rogue_device_99",
            "download_mb": 5.0,
            "files_accessed": 100,
            "accessed_department": "Top Secret Engineering Data"
        }
    ]
    
    return events

def run_simulation():
    """
    Loops through the demo events, sending them to the FastAPI server with delays.
    """
    # Check health first
    try:
        health = requests.get(f"{BASE_URL}/health")
        if health.status_code != 200:
            print(f"Error: Server responded with status {health.status_code}")
            return
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Could not connect to the server.")
        print("Please ensure main.py is running in a separate terminal before starting this simulation.")
        print("Run: uvicorn main:app --host 0.0.0.0 --port 8000 --reload")
        return

    events = get_demo_events()
    total_sent = 0
    high_risk_flagged = 0

    print("=" * 60)
    print("🚀 STARTING REAL-TIME SIMULATION...")
    print("=" * 60)
    print(f"Sending {len(events)} events to the UEBA engine...\n")

    for i, event in enumerate(events):
        event['timestamp'] = datetime.now().isoformat() # Update timestamp to current
        
        # Log before sending
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Sending event {i+1}/{len(events)} for user {event['user_id']}...")
        
        try:
            res = requests.post(f"{BASE_URL}/simulate-event", json=event, headers=HEADERS)
            if res.status_code == 200:
                data = res.json()
                score = data.get("final_risk_score", 0)
                reasons = data.get("reasons", [])
                
                if score > 60:
                    high_risk_flagged += 1
                    reasons_str = ", ".join(reasons)
                    print(f"   🚨 HIGH RISK DETECTED! Score: {score}, Reasons: {reasons_str}")
                else:
                    print(f"   ✅ Normal activity. Score: {score}")
            else:
                print(f"   ❌ Failed to process event. Server responded with {res.status_code}: {res.text}")
        except Exception as e:
            print(f"   ❌ Error sending event: {e}")
            
        total_sent += 1
        
        # Wait before next event
        if i < len(events) - 1:
            time.sleep(3)
            
    print("\n" + "=" * 60)
    print("🏁 SIMULATION COMPLETE")
    print("=" * 60)
    print(f"Total events sent: {total_sent}")
    print(f"High risk events flagged: {high_risk_flagged}")

if __name__ == "__main__":
    run_simulation()
