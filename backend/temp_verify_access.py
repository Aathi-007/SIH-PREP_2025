from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_access_request():
    print("1. Logging in as christina.moran (Sales)...")
    login_response = client.post("/login", json={
        "username": "christina.moran",
        "password": "password123"
    })
    
    if login_response.status_code != 200:
        print("Login failed!", login_response.text)
        return
        
    token = login_response.json().get("access_token")
    headers = {
        "Authorization": f"Bearer {token}",
        "X-API-Key": "dev-local-key"
    }
    
    print("\n2. Requesting access to RES004 (Sales)...")
    res1 = client.post("/access-request", headers=headers, json={"resource_id": "RES004"})
    print("Status:", res1.status_code)
    print("Response:", res1.json())
    
    print("\n3. Requesting access to RES001 (Finance)...")
    res2 = client.post("/access-request", headers=headers, json={"resource_id": "RES001"})
    print("Status:", res2.status_code)
    print("Response:", res2.json())

if __name__ == "__main__":
    test_access_request()
