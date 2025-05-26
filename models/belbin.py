from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime, Boolean
from sqlalchemy.orm import relationship
from db.database import Base


class BelbinRole(Base):
    __tablename__ = "belbin_roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)
    created_by_id = Column(Integer, ForeignKey('employees.id', ondelete="CASCADE"))

    questions = relationship("BelbinAnswer", back_populates="role")
    position_requirements = relationship("BelbinPositionRequirement", back_populates="role")
    results = relationship("BelbinTestResult", back_populates="role")
    created_by = relationship("Employee", back_populates="created_roles")  

class BelbinQuestion(Base):
    __tablename__ = "belbin_questions"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, index=True, nullable=False)   
    block_number = Column(Integer)
    order = Column(Integer, nullable=False)
    test_id = Column(Integer, ForeignKey("tests.id", ondelete="CASCADE"))  

    test = relationship("Test", back_populates="belbin_questions")  
    answers = relationship("BelbinAnswer", back_populates="question")



class BelbinAnswer(Base):
    __tablename__ = "belbin_answers"

    id = Column(Integer, primary_key=True, index=True)
    # test_id = Column(Integer, ForeignKey("test.id"))
    question_id = Column(Integer, ForeignKey("belbin_questions.id", ondelete="CASCADE"))
    score = Column(Integer, nullable=True)  # 0-10 баллов
    role_id = Column(Integer, ForeignKey("belbin_roles.id", ondelete="CASCADE"))
    text = Column(String, nullable=False)  

    role = relationship("BelbinRole", back_populates="questions")
    # test = relationship("Test", back_populates="belbin_answers")
    question = relationship("BelbinQuestion", back_populates="answers")
    user_answers = relationship("UserBelbinAnswer", back_populates="answer")


class BelbinTestResult(Base):
    __tablename__ = "belbin_test_results"

    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey("test_results.id", ondelete="CASCADE")) 
    role_id = Column(Integer, ForeignKey("belbin_roles.id", ondelete="CASCADE"))
    total_score = Column(Float)
    # is_required = Column(Boolean)
    # meets_requirement = Column(Boolean)

    test_result = relationship("TestResult", back_populates="belbin_results")
    role = relationship("BelbinRole", back_populates="results")


class BelbinPositionRequirement(Base):
    __tablename__ = "belbin_position_requirements"

    id = Column(Integer, primary_key=True, index=True)
    position_id = Column(Integer, ForeignKey("positions.id", ondelete="CASCADE"))
    role_id = Column(Integer, ForeignKey("belbin_roles.id", ondelete="CASCADE"))
    min_score = Column(Integer)
    is_key = Column(Boolean)  # Является ли роль ключевой для должности

    position = relationship("Position", back_populates="belbin_requirements")
    role = relationship("BelbinRole", back_populates="position_requirements")
