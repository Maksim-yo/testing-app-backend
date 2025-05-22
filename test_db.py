from sqlalchemy.orm import sessionmaker
from db.database import engine
from datetime import datetime
from models import Employee, Test, Position, Question, Answer

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

# Создаем тестовые должности
position1 = Position(title="Developer", description="Software Developer", salary=1000)
position2 = Position(title="Manager", description="Project Manager", salary=2000)

# db.add(position1)
# db.add(position2)
# db.commit()

# Создаем тестовых сотрудников
employee1 = Employee(
    last_name="Doe", 
    first_name="John", 
    middle_name="Middle", 
    birth_date=datetime(1990, 1, 1), 
    phone="123-456-7890", 
    email="john.doe@example.com", 
    position_id=position1.id, 
    hire_date=datetime(2020, 5, 1),
    is_admin=False
)

employee2 = Employee(
    last_name="Smith", 
    first_name="Jane", 
    middle_name="Ann", 
    birth_date=datetime(1985, 5, 15), 
    phone="987-654-3210", 
    email="jane.smith@example.com", 
    position_id=position2.id, 
    hire_date=datetime(2018, 3, 20),
    is_admin=True
)

db.add(employee1)
db.add(employee2)
db.commit()

# Создаем тест
test = Test(
    title="Tech Interview",
    description="Test for assessing technical knowledge.",
    position_id=position1.id,
    created_by=employee1.id,  # Идентификатор создателя теста
    time_limit_minutes=60
)

db.add(test)
db.commit()

# Создаем вопросы для теста
question1 = Question(
    text="What is 2 + 2?",
    test_id=test.id
)

answer1 = Answer(text="3", is_correct=False, question_id=question1.id)
answer2 = Answer(text="4", is_correct=True, question_id=question1.id)
answer3 = Answer(text="5", is_correct=False, question_id=question1.id)

db.add(question1)
db.add(answer1)
db.add(answer2)
db.add(answer3)
db.commit()

# Назначаем тест сотрудникам
test.assigned_to.append(employee1)
test.assigned_to.append(employee2)

db.commit()

# Закрываем сессию
db.close()
