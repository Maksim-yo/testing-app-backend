from fastapi.testclient import TestClient
from main import app
from .test_database import client
from tests.test_data import get_test_position_data

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert "html" in response.headers["content-type"]

def test_get_quiz():
    response = client.get("/api/quiz?questions=3")
    assert response.status_code == 200
    assert "questions" in response.json()

def test_submit_quiz():
    payload = {
        "user_id": 1,
        "answers": ["a", "b", "c"]
    }
    response = client.post("/submit-quiz", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_create_position():
    payload = get_test_position_data()
    response = client.post("/positions/", json=payload)
    assert response.status_code == 200
    assert "id" in response.json()
    assert response.json()["name"] == "Test Position"

def test_read_positions():
    response = client.get("/positions/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_read_employees():
    response = client.get("/employees/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
