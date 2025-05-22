from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime


class BelbinRoleBase(BaseModel):
    name: str
    description: Optional[str] = None


class BelbinRoleCreate(BelbinRoleBase):
    pass


class BelbinRole(BelbinRoleBase):
    id: int

    class Config:
        from_attributes = True  


class BelbinAnswerBase(BaseModel):
    text: str
    role_id: int


class BelbinAnswerCreate(BelbinAnswerBase):
    pass

class BelbinAnswer(BelbinAnswerBase):
    id: int
    role_name: str  

    class Config:
        from_attributes = True  

class BelbinQuestionBase(BaseModel):
    text: str
    block_number: int
    order: int
    question_type: Literal["belbin"] = "belbin"


class BelbinQuestionCreate(BelbinQuestionBase):
    answers: List[BelbinAnswerCreate]




class BelbinQuestion(BelbinQuestionBase):
    id: int
    test_id: int
    answers: List[BelbinAnswer] 

    class Config:
        from_attributes = True  



class BelbinTestBase(BaseModel):
    employee_id: int


class BelbinTestCreate(BelbinTestBase):
    answers: List[BelbinAnswerCreate]


class BelbinTest(BelbinTestBase):
    id: int
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True  


class BelbinTestResult(BaseModel):
    id: int
    role_id: int
    total_score: int
    role: Optional[BelbinRole] = None

    class Config:
        orm_mode = True
        from_attributes=True

class BelbinTestEvaluation(BaseModel):
    test_id: int
    employee_name: str
    position_name: str
    overall_result: str  # "high", "medium", "low"
    results: List[BelbinTestResult]

    class Config:
        from_attributes = True  



class BelbinRequirementItemBase(BaseModel):
    role_id: int
    role_name: str
    role_description: str
    min_score: int
    is_key: bool
    position_id: int

class BelbinRequirementItem(BaseModel):
    id: Optional[int] = None  
    role_id: int
    role_name: str
    role_description: str
    min_score: int
    is_key: bool
    position_id: int


class BelbinPositionRequirementBase(BaseModel):
    position_id: int
    requirements: List[BelbinRequirementItemBase]


class BelbinPositionRequirementCreate(BelbinPositionRequirementBase):
    pass



class BelbinPositionRequirement(BaseModel):

    position_id: int
    requirements: List[BelbinRequirementItem]

    class Config:
        from_attributes = True  


class BelbinRequirementSchema(BaseModel):
    role: BelbinRole
    min_score: int
    is_key: bool

    class Config:
        orm_mode = True
        from_attributes = True  

class PositionSchema(BaseModel):
    id: int
    title: str
    belbin_requirements: list[BelbinRequirementSchema]

    class Config:
        orm_mode = True
        from_attributes = True  
