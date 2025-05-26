from sqlalchemy.orm import Session
from models import employee as model
from schemas import employee as schema
from datetime import date
from fastapi import HTTPException, status
from crud.test import get_current_user, check_user_permissions
from typing import Union
from models.test import test_assignments
from sqlalchemy.exc import IntegrityError
from psycopg2.errors import UniqueViolation

def create_account(db:Session, employee: schema.EmployeeMinimal):
    try:
        existing_user = db.query(model.Employee).filter_by(clerk_id=employee.clerk_id).first()
        if existing_user:
            raise HTTPException(status_code=404, detail="user already exists.")
        if employee.email == "":
            employee.email = None  # или выбросить ошибку
        # Создаём нового пользователя
        new_user = model.Employee(
            **employee.dict()
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except IntegrityError as e:
            # Проверяем, что причина ошибки - UniqueViolation (дубликат по уникальному ключу)
            if isinstance(e.orig, UniqueViolation):
                if 'employees_email_key' in str(e.orig):
                    raise HTTPException(
                        status_code=400,
                        detail="Пользователь с таким email уже существует."
                    )
            # Если ошибка не обрабатывается, пробрасываем дальше с обобщенным сообщением
            raise HTTPException(status_code=500, detail=f"Ошибка создания сотрудника: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка создания сотрудника: {str(e)}")


def get_employee(db: Session, employee_id: int, user_id: str):
    user = get_current_user(db, user_id)
    try:
        db_employee = db.query(model.Employee).filter(model.Employee.id == employee_id).first()
        if not db_employee:
            raise HTTPException(status_code=404, detail="Employee not found.")
        if db_employee.created_by_id != user.id:
            raise HTTPException(status_code=403, detail="You do not have permission to get this employee.")    
        return db_employee
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving employee: {str(e)}")

def delete_current_user(db: Session, user_id: str):
    try:
        user = get_current_user(db, user_id)
        db.delete(user)
        db.commit()
        return user
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting current user: {str(e)}")

def get_employees(db: Session, user_id: str):
    try:
        user = check_user_permissions(db, user_id, True)
        employees = db.query(model.Employee).filter(model.Employee.created_by_id == user.id).all()
      
        return employees
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving employees: {str(e)}")

def create_employee(db: Session, employee: Union[schema.EmployeeCreate, schema.EmployeeCreateMinimal], photo: Union[bytes, None], user_id: str, employee_id: str):
    try:
        user = check_user_permissions(db, user_id, True)
        if employee.email == "":
            employee.email = None  # или выбросить ошибку
        db_employee = model.Employee(
            **employee.dict(exclude={"photo"}),
            created_by_id=user.id,
        )
        if photo:
            db_employee.photo = photo
        db.add(db_employee)
        db.commit()
        db.refresh(db_employee)
        return schema.Employee.model_validate(db_employee)
    except IntegrityError as e:
        # Проверяем, что причина ошибки - UniqueViolation (дубликат по уникальному ключу)
        if isinstance(e.orig, UniqueViolation):
            # Можно более точно проверить текст ошибки, чтобы убедиться, что это именно по email
            if 'employees_email_key' in str(e.orig):
                raise HTTPException(
                    status_code=400,
                    detail="Пользователь с таким email уже существует."
                )
        # Если ошибка не обрабатывается, пробрасываем дальше с обобщенным сообщением
        raise HTTPException(status_code=500, detail=f"Ошибка создания сотрудника: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка создания сотрудника: {str(e)}")

def delete_employee(db: Session, employee_id: str, user_id: str):
    try:
        user = check_user_permissions(db, user_id, True)
        db_employee = db.query(model.Employee).filter(model.Employee.id == employee_id).first()
        if not db_employee:
            raise HTTPException(status_code=404, detail="Employee not found.")
        if db_employee.created_by_id != user.id:
            raise HTTPException(status_code=403, detail="You do not have permission to delete this employee.")    
        db.execute(
            test_assignments.delete().where(test_assignments.c.employee_id == user.id)
        )

        db.delete(db_employee)
        db.commit()
        return {"detail": "Employee deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting employee: {str(e)}")

def update_employee(db: Session, employee_id: int, employee_update: schema.EmployeeCreate, photo: Union[bytes, None], user_id: str):
    try:
        user = check_user_permissions(db, user_id, True)
        db_employee = db.query(model.Employee).filter(model.Employee.id == employee_id, model.Employee.created_by_id == user.id).first()

        if not db_employee:
            raise HTTPException(status_code=404, detail="Employee not found.")
        
        for field, value in employee_update.dict(exclude_unset=True, exclude_none=True, exclude=["is_admin"]).items():
            setattr(db_employee, field, value)
        if photo is not None:
            setattr(db_employee, "photo", photo)
            
        db.commit()
        db.refresh(db_employee)
        return schema.Employee.model_validate(db_employee)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating employee: {str(e)}")

def update_profile(db: Session, user_update: schema.EmployeeCreate, photo: Union[bytes, None], user_id: str):
    try:
        user = get_current_user(db, user_id)
        for field, value in user_update.dict(exclude_unset=True, exclude_none=True, exclude=["is_admin"]).items():
            setattr(user, field, value)
        if photo is not None:
            setattr(user, "photo", photo)
        db.commit()
        db.refresh(user)
        return schema.Employee.model_validate(user, from_attributes=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating profile: {str(e)}")
