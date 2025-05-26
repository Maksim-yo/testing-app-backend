from sqlalchemy import Column, Integer, String, Date, ForeignKey, Boolean
from sqlalchemy.sql.sqltypes import LargeBinary
from sqlalchemy.orm import relationship

from db.database import Base
from models.test import test_assignments

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    last_name = Column(String, index=True, nullable=True)
    first_name = Column(String, nullable=True)
    middle_name = Column(String, nullable=True)
    birth_date = Column(Date, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True, unique=True)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=True)
    hire_date = Column(Date, nullable=True)
    photo = Column(LargeBinary, nullable=True)  # Для хранения бинарных данных фото
    photo_url = Column(String, nullable=True)   # Альтернативно: URL к фото

    is_admin = Column(Boolean, default=False)

    created_by_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=True)
    clerk_id = Column(String, unique=True, index=True, nullable=True)  # Идентификатор из Clerk

    created_roles = relationship("BelbinRole", back_populates="created_by")  # Добавлено
    position = relationship("Position", back_populates="employees", foreign_keys=[position_id])
    created_tests = relationship(
        "Test",
        back_populates="created_by_user",
        foreign_keys="[Test.created_by]",
        cascade="all, delete-orphan"
    )
    created_positions = relationship("Position", back_populates="created_by", foreign_keys="[Position.created_by_id]", cascade="all, delete-orphan")
    user_answers = relationship("UserAnswer", back_populates="employee", cascade="all, delete-orphan")

    results = relationship("TestResult", back_populates="employee", cascade="all, delete-orphan")
    created_by = relationship("Employee", remote_side=[id], backref="created_employees")

    assigned_tests = relationship(
        "Test",
        secondary=test_assignments,
        back_populates="assigned_to"
    )

class UserAnswer(Base):
    __tablename__ = "user_answers"

    id = Column(Integer, primary_key=True, index=True)

    test_id = Column(Integer, ForeignKey("tests.id", ondelete="CASCADE"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"))
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    answer_id = Column(Integer, ForeignKey("answers.id", ondelete="CASCADE"), nullable=True)  # для выбора
    text_response = Column(String, nullable=True)  # для текстовых ответов

    test = relationship("Test")
    employee = relationship("Employee")
    question = relationship("Question")
    answer = relationship("Answer", foreign_keys=[answer_id])


class UserBelbinAnswer(Base):
    __tablename__ = "user_belbin_answers"

    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey("tests.id", ondelete="CASCADE"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(Integer, ForeignKey("belbin_questions.id", ondelete="CASCADE"), nullable=False)
    answer_id = Column(Integer, ForeignKey("belbin_answers.id", ondelete="CASCADE"), nullable=False)  # 🔥 связь с ответом!

    score = Column(Integer, nullable=True)

    test = relationship("Test")
    employee = relationship("Employee")
    question = relationship("BelbinQuestion")
    answer = relationship("BelbinAnswer", back_populates="user_answers")

class UserAnswerItem(Base):
    __tablename__ = "user_answer_items"
    
    id = Column(Integer, primary_key=True, index=True)
    user_answer_id = Column(Integer, ForeignKey("user_answers.id", ondelete="CASCADE"))
    answer_id = Column(Integer, ForeignKey("answers.id", ondelete="CASCADE"))

    answer = relationship("Answer", foreign_keys=[answer_id])
