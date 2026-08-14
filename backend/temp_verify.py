from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_login():
    print("Testing /login endpoint...")
    response = client.post("/login", json={
        "username": "christina.moran",
        "password": "password123"
    })
    
    if response.status_code == 200:
        print("Login SUCCESS!")
        print("Response:", response.json())
        token = response.json().get("access_token")
        import jwt
        decoded = jwt.decode(token, options={"verify_signature": False})
        print("Decoded token:", decoded)
    else:
        print("Login FAILED!")
        print("Status:", response.status_code)
        print("Response:", response.text)

if __name__ == "__main__":
    test_login()
