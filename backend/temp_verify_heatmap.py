from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_heatmap():
    print("1. Logging in as christina.moran...")
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
    
    print("\n2. Requesting /analytics/daily-risk...")
    res = client.get("/analytics/daily-risk", headers=headers)
    print("Status:", res.status_code)
    print("Response sample:", res.json()[:3])

if __name__ == "__main__":
    test_heatmap()
