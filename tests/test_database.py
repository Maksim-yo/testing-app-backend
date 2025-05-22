# tests/test_database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.database import Base
from fastapi.testclient import TestClient
from main import app, get_db

# Используем SQLite в памяти для тестов
SQLALCHEMY_DATABASE_URL = "sqlite:///./test1.db"  # или sqlite:///:memory: для in-memory

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создаем таблицы
Base.metadata.create_all(bind=engine)

# Заменяем зависимость get_db на тестовую
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)
