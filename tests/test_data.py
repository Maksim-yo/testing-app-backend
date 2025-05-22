from datetime import date
from schemas.employee import  EmployeeCreate
from schemas.positions import PositionCreate
from schemas.test import TestCreate, QuestionCreate, AnswerCreate

def get_test_quiz_data(position_id: int):
    return TestCreate(
        title="Тест по продукту",
        description="Базовый тест по продуктам компании",
        position_id=position_id,
        time_limit_minutes=20,
        questions=[
            QuestionCreate(
                text="Какой наш основной продукт?",
                question_type="single_choice",
                answers=[
                    AnswerCreate(text="Продукт A", is_correct=True),
                    AnswerCreate(text="Продукт B", is_correct=False),
                    AnswerCreate(text="Продукт C", is_correct=False)
                ]
            ),
            QuestionCreate(
                text="Какие функции есть в продукте?",
                question_type="multiple_choice",
                answers=[
                    AnswerCreate(text="Функция 1", is_correct=True),
                    AnswerCreate(text="Функция 2", is_correct=True),
                    AnswerCreate(text="Функция 3", is_correct=False)
                ]
            )
        ]
    )

def get_test_position_data():
    return PositionCreate(
        title="Тестовая должность",
        description="Описание тестовой должности",
        salary=50000,
        access_level="medium",
        has_system_access=True
    )

def get_test_employee_data(position_id: int):
    return EmployeeCreate(
        last_name="Иванов",
        first_name="Иван",
        middle_name="Иванович",
        birth_date=date(1990, 1, 1),
        phone="+79991234567",
        email="ivanov@test.com",
        position_id=position_id,
        hire_date=date(2020, 1, 1)
    )