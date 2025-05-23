from pydantic import BaseModel
from typing import List, Optional, Literal
from datetime import datetime

from schemas.employee import Employee
from schemas.belbin import BelbinQuestionCreate, BelbinQuestion, BelbinTestResult
from enum import Enum

class TestStatusEnum(str, Enum):
    draft = "draft"
    active = "active"
    archive = "archive"

class TestStatusUpdate(BaseModel):
    status: TestStatusEnum

class AnswerBase(BaseModel):
    text: str
    is_correct: bool = False
    image: Optional[bytes] = None  # 🔥


class AnswerCreate(AnswerBase):
    pass


class Answer(AnswerBase):
    id: int
    question_id: int

    class Config:
        from_attributes = True  


class QuestionBase(BaseModel):
    text: str
    question_type: str = "single_choice"  # single_choice/multiple_choice/text_answer
    image: Optional[bytes] = None  # 🔥
    order: int
    points: int
    question_type: Literal["single_choice", "multiple_choice", "text_answer"] = "single_choice"

class QuestionCreate(QuestionBase):
    answers: List[AnswerCreate] = []


class Question(QuestionBase):
    id: int
    test_id: int
    answers: List[Answer] = []
    points: int

    class Config:
        from_attributes = True  

class TestSettingsBase(BaseModel):
    min_questions: int
    belbin_block: int
    belbin_questions_in_block: int
    
class TestSettingsCreate(TestSettingsBase):
    pass

class TestSettings(TestSettingsBase):
    id: int

    class Config:
        from_attributes = True  

class TestBase(BaseModel):
    title: str
    description: Optional[str] = None
    is_active: bool = True 
    end_date: datetime
    image: Optional[bytes] = None  # 🔥
    time_limit_minutes: Optional[int] = None
    status: str

class TestCreate(TestBase):
    questions: List[QuestionCreate] = []
    belbin_questions: List[BelbinQuestionCreate] = []
    test_settings: TestSettingsCreate


class Test(TestBase):
    id: int
    created_at: datetime = 0
    updated_at: datetime = 0
    questions: List[Question] = []
    assigned_to: List[Employee] = []
    belbin_questions: List[BelbinQuestion] = []
    test_settings: TestSettings
    status: str
    class Config:
        from_attributes = True  


class TestWithAnswersSchema(TestBase):
    id: int
    answers: List["UserAnswer"]  
    class Config:
        orm_mode = True  


class UserAnswerBase(BaseModel):
    test_id: int
    question_id: int
    answer_ids: List[int] = []  # Для multiple choice
    text_response: Optional[str] = None  # belbin or ordinary text answer
    question_type: Literal["single_choice", "multiple_choice", "text_answer", "belbin"]

class UserAnswerCreate(UserAnswerBase):
    pass

class UserAnswer(UserAnswerBase):
    id: int

    class Config:
        orm_mode = True

class TestAssignmentItem(BaseModel):
    employee_id: int
    test_id: int

class TestAssignmentBase(BaseModel):
    assignments: List[TestAssignmentItem]

class TestAssignmentCreate(TestAssignmentBase):
    pass

class UserAnswerSchema(BaseModel):
    id: int
    question_id: int
    answer_ids: List[int] = []
    text_response: Optional[str] = None

    class Config:
        from_attributes = True

class SafeAnswer(BaseModel):
    id: Optional[int]
    question_id: int
    text: str
    image: Optional[bytes] = None
    is_user_answer: bool = False  # ✅ Добавлено

class SafeQuestion(BaseModel):
    id: int
    text: str
    question_type: Literal["single_choice", "multiple_choice", "text_answer"]
    order: int
    answers: List[SafeAnswer]  # Используем SafeAnswer вместо Answer
    image: Optional[bytes] = None  # 🔥
    test_id: int
    class Config:
        from_attributes = True


class SafeBelbinAnswer(BaseModel):
    id: int
    question_id: int
    text: str  # ⚠️ не включаем score и role_id
    user_score: Optional[int] = None  # ✅ Добавлено

    class Config:
        from_attributes = True


class SafeBelbinQuestion(BaseModel):
    id: int
    text: str
    block_number: Optional[int]
    order: int
    test_id: int
    answers: List[SafeBelbinAnswer]

    class Config:
        from_attributes = True

class SafeTest(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    is_active: bool
    end_date: datetime
    status: str
    created_at: datetime
    updated_at: datetime
    questions: List[SafeQuestion]  # Используем SafeQuestion
    belbin_questions: List[SafeBelbinQuestion]
    time_limit_minutes: Optional[int] = None
    started_at: Optional[datetime] = None
    class Config:
        from_attributes = True
# class TestAssignment(TestAssignmentBase):
#     class Config:
#         orm_mode = True

class TestResultSchema(BaseModel):
    id: int
    test_id: int
    employee_id: int
    is_completed: bool
    completed_at: Optional[datetime]
    started_at: datetime
    score: Optional[int]
    max_score: Optional[int]
    percent: Optional[float]
    time_limit_minutes: Optional[int]

    employee: Optional[Employee] = None
    belbin_results: List[BelbinTestResult] = []

    class Config:
        orm_mode = True
        from_attributes=True