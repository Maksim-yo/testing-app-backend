from pydantic import BaseModel
from typing import List, Dict

class Question(BaseModel):
    id: int
    text: str
    options: List[str]
    correct_answer: int  # индекс правильного ответа

class Quiz(BaseModel):
    title: str
    questions: List[Question]