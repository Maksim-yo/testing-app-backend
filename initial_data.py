from sqlalchemy.orm import Session
from models import belbin as models

def init_belbin_roles(db: Session):
    roles = [
        {"name": "Генератор идей", "description": "Сотрудник, который быстро предлагает нестандартные решения"},
        {"name": "Координатор", "description": "Способен организовывать людей, управлять процессами"},
        {"name": "Аналитик", "description": "Внимательный, склонный к глубокому анализу информации"},
        {"name": "Душа команды", "description": "Поддерживает атмосферу в коллективе, избегает конфликтов"},
        {"name": "Исследователь ресурсов", "description": "Ищет полезную информацию и связи вне команды"},
        {"name": "Исполнитель", "description": "Стабильно и надёжно выполняет задачи"},
        {"name": "Реализатор", "description": "Умеет структурировать работу, действует чётко"},
        {"name": "Контролёр завершения", "description": "Внимателен к деталям, следит за качеством"},
        {"name": "Мотиватор", "description": "Хорошо вдохновляет и мотивирует команду"}
    ]

    for role_data in roles:
        db_role = models.BelbinRole(**role_data)
        db.add(db_role)

    db.commit()

def init_belbin_questions(db: Session):
    questions = [
        {"text": "Я могу быстро придумать оригинальные идеи и решения", "block_number": 1, "role_id": 1},
        {"text": "Я умею организовать работу команды", "block_number": 1, "role_id": 2},
        # Добавьте остальные вопросы по аналогии
    ]

    for question_data in questions:
        db_question = models.BelbinQuestion(**question_data)
        db.add(db_question)

    db.commit()

def init_position_requirements(db: Session):
    requirements = [
        {"position_id": 1, "role_id": 1, "min_score": 5, "is_key": True},  # Руководитель
        {"position_id": 1, "role_id": 2, "min_score": 8, "is_key": True},
        # Добавьте остальные требования по аналогии
    ]

    for req_data in requirements:
        db_req = models.BelbinPositionRequirement(**req_data)
        db.add(db_req)

    db.commit()