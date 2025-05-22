from fastapi import status
from crud import employee as crud_employee
from crud import positions as crud_position
from tests.test_data import get_test_position_data, get_test_employee_data
from fastapi.encoders import jsonable_encoder


def test_create_employee(client, db_session):
    
    position_data = get_test_position_data()
    position = crud_position.create_position(db_session, position_data)


    employee_data = get_test_employee_data(position.id)
    response = client.post(
        "/employees/",
        json=employee_data.model_dump(mode="json")
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["last_name"] == employee_data.last_name
    assert data["position_id"] == position.id


def test_get_employees(client, db_session):
    # Создаем тестовые данные
    position = crud_position.create_position(db_session, get_test_position_data())
    crud_employee.create_employee(db_session, get_test_employee_data(position.id))

    # Получаем список
    response = client.get("/employees/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) > 0
    assert data[0]["last_name"] == "Иванов"