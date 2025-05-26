from pydantic import BaseModel, Field, EmailStr, constr, field_serializer
from typing import Optional, List
from datetime import date
from enum import Enum
from fastapi import  UploadFile, File, Form
import base64

from schemas.positions import Position
from schemas.belbin import PositionSchema

class AccountCreateType(str, Enum):
    link = "link"          # регистрация по ссылке
    email_password = "email_password"  # email + пароль
    username_password = "username_password"  # логин + пароль

class EmployeeBase(BaseModel):
    last_name: Optional[str] = None
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    birth_date: Optional[date] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    position_id: Optional[int] = None
    hire_date: Optional[date] = None
    is_admin: bool = False
    clerk_id: Optional[str] = None  

class EmployeeMinimalBase(BaseModel):
    email: str
    is_admin: bool = False

class EmployeeCreateMinimal(EmployeeMinimalBase):
    pass

class EmployeeMinimal(EmployeeMinimalBase):
    clerk_id: str

class EmployeeCreate(EmployeeBase):
    # photo: Optional[bytes] = None  # здесь поле для файла
    photo_url: Optional[str] = None  # Альтернативно: URL
    class Config:
        arbitrary_types_allowed = True

class Employee(EmployeeBase):
    id: int
    photo_url: Optional[str] = None
    photo: Optional[bytes] = None  # Храним как bytes
    position: Optional[PositionSchema] = None

    @field_serializer('photo')
    def serialize_photo(self, photo: Optional[bytes], _info):
        if photo is None:
            return None
        return base64.b64encode(photo).decode('utf-8')

    class Config:
        from_attributes = True  
        arbitrary_types_allowed = True

class EmployeeCreateWithAccount(Employee):
    type: AccountCreateType  # тип создания аккаунта

    # только если type = username_password
    username: Optional[str] = None

    # только если type = username_password или email_password
    password: Optional[str] = None

    # только если type = email_password или link
def as_form_with_file(cls):
    def _as_form(
        first_name: str = Form(None),
        last_name: str = Form(None),
        email: str = Form(None),
        phone: Optional[str] = Form(None),
        position_id: int = Form(None),
        birth_date: Optional[date] = Form(None),
        hire_date: Optional[date] = Form(None),
        middle_name: Optional[str] = Form(None),
        is_admin: bool = Form(False),
        clerk_id: Optional[str] = Form(None),
        created_by_id: Optional[int] = Form(None),
    ):
        return cls(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            position_id=position_id,
            birth_date=birth_date,
            hire_date=hire_date,
            middle_name=middle_name,
            is_admin=is_admin,
            clerk_id=clerk_id,
            created_by_id=created_by_id,
        )
    return _as_form

EmployeeCreate.as_form = as_form_with_file(EmployeeCreate)

