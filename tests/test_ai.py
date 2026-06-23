from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def get_auth_token():
    import random
    email = f"aitest{random.randint(1,99999)}@gmail.com"
    create_response = client.post("/api/v1/generate-api", json={
        "name": "AI Test User",
        "email": email,
        "password": "123456",
        "role": "user"
    })
    print("CREATE USER RESPONSE:", create_response.json())
    response = client.post("/api/v1/login", json={
        "email": email,
        "password": "123456"
    })
    print("LOGIN RESPONSE:", response.json())
    return response.json()["token"]

def test_get_templates():
    response = client.get("/api/v1/ai/templates")
    assert response.status_code == 200
    assert "templates" in response.json()

def test_generate_api():
    token = get_auth_token()
    response = client.post("/api/v1/ai/generate",
        json={
            "description": "create a simple notes API",
            "provider": "groq"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_get_history():
    token = get_auth_token()
    response = client.get("/api/v1/ai/history",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "history" in response.json()

def test_get_stats():
    token = get_auth_token()
    response = client.get("/api/v1/ai/stats",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "total_generations" in response.json()