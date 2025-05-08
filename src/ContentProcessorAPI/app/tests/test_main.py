from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"message": "I'm alive!"}
    assert response.headers["Custom-Header"] == "liveness probe"


def test_startup():
    response = client.get("/startup")
    assert response.status_code == 200
    assert "Running for" in response.json()["message"]
    assert response.headers["Custom-Header"] == "Startup probe"
