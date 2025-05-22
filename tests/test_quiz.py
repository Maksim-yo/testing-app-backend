from fastapi import status
from schemas.test import Test, Question
from tests.test_data import get_test_quiz_data


def test_create_test(client):
    test_position_id = 2
    test_data = get_test_quiz_data(test_position_id)
    response = client.post("/tests/", json=test_data.model_dump())

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["title"] == test_data.title
    assert len(data["questions"]) == 2
    assert len(data["questions"][0]["answers"]) == 3


def test_get_tests_by_position(client):
    # Сначала создаем тест
    test_position_id = 2
    test_data = get_test_quiz_data(test_position_id)
    client.post("/tests/", json=test_data.model_dump())

    # Получаем тесты для должности
    response = client.get(f"/positions/{test_position_id}/tests/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) > 0
    assert data[0]["position_id"] == test_position_id