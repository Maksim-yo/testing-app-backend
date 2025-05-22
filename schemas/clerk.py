from pydantic import BaseModel, EmailStr
from typing import List, Optional
from enum import Enum


class ClerkRole(str, Enum):
    ADMIN = "admin"
    EMPLOYEE = "employee"


class ClerkMetadata(BaseModel):
    role: ClerkRole
    is_admin: bool


class ClerkPublicMetadata(BaseModel):
    user_type: ClerkRole


class ClerkUserCreate(BaseModel):
    email_address: List[EmailStr]
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    unsafe_metadata: ClerkMetadata
    public_metadata: ClerkPublicMetadata
