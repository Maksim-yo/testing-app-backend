from pydantic import BaseModel
from typing import Optional

class PositionBase(BaseModel):
    title: str
    description: Optional[str] = None
    access_level: str = "basic"
    salary: int
    has_system_access: bool = False

class PositionCreate(PositionBase):
    pass

class Position(PositionBase):
    id: int

    class Config:
        from_attributes = True  