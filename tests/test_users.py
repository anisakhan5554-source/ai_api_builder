from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200

def test_create_user():
    import random
    random_email=f"test{random.randint(1,99999)}@gmail.com"
    response = client.post("/api/users", json={
        "name": "TestUser",
        "email": random_email,
        "password": "123456",
        "role": "user"
    })
    assert response.status_code == 200

def test_get_users():
    response = client.get("/api/users")
    assert response.status_code == 200