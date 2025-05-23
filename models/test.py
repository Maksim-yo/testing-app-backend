from sqlalchemy import Column, Integer,String, Boolean, ForeignKey, DateTime, Table, LargeBinary, Float
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from db.database import Base
from models.belbin import BelbinQuestion
import pytest

test_assignments = Table(
    "test_assignments",
    Base.metadata,
    Column("test_id", Integer, ForeignKey("tests.id"), primary_key=True),
    Column("employee_id", Integer, ForeignKey("employees.id"), primary_key=True),
)
class TestSettings(Base):
    __tablename__ = "test_settings"

    id = Column(Integer, primary_key=True, index=True)
    min_questions = Column(Integer, nullable=False)
    belbin_block = Column(Integer, nullable=False)
    belbin_questions_in_block = Column(Integer, nullable=False)
    has_time_limit = Column(Boolean, nullable=False)
    tests = relationship("Test", back_populates="test_settings", cascade="all, delete")  

class Test(Base):
    __tablename__ = "tests"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    time_limit_minutes = Column(Integer, nullable=True)

    image = Column(LargeBinary, nullable=True)  # 🔥 Хранение изображения
    status = Column(String, default="draft")
    test_settings_id = Column(Integer, ForeignKey("test_settings.id")) 
    created_by = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"))
    end_date = Column(DateTime(timezone=True), default=None)

    assigned_to = relationship("Employee", secondary=test_assignments, back_populates="assigned_tests")
    questions = relationship("Question", back_populates="test", cascade="all, delete")
    belbin_questions = relationship("BelbinQuestion", back_populates="test", cascade="all, delete")  # 🔥
    results = relationship("TestResult", back_populates="test", cascade="all, delete-orphan")

    created_by_user = relationship("Employee", back_populates="created_tests", foreign_keys=[created_by])
    test_settings = relationship("TestSettings", back_populates="tests", cascade="all, delete")



class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, index=True, nullable=False)
    test_id = Column(Integer, ForeignKey("tests.id"))
    question_type = Column(String, default="single_choice")  # single_choice/multiple_choice/text_answer
    image = Column(LargeBinary, nullable=True)  
    order = Column(Integer, nullable=False)
    points = Column(Integer, default=1, nullable=False)  

    test = relationship("Test", back_populates="questions")
    answers = relationship("Answer", back_populates="question", cascade="all, delete")


class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String)
    is_correct = Column(Boolean, default=False)
    question_id = Column(Integer, ForeignKey("questions.id"))
    image = Column(LargeBinary, nullable=True)  # 🔥

    question = relationship("Question", back_populates="answers")


class TestResult(Base):
    __tablename__ = "test_results"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    test_id = Column(Integer, ForeignKey("tests.id"))
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"))

    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime, default=datetime.now(timezone.utc))  # Дата начала теста

    score = Column(Integer, nullable=True)
    max_score = Column(Integer, nullable=True)
    percent = Column(Float, nullable=True)


    belbin_results = relationship("BelbinTestResult", back_populates="test_result", cascade="all, delete")
    test = relationship("Test", back_populates="results")
    employee = relationship("Employee", back_populates="results")