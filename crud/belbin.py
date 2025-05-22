from sqlalchemy.orm import Session
from schemas import belbin as schemas
from models import belbin as model
from models import Position, BelbinRole, Employee
from schemas import belbin as schema
from typing import List
from fastapi import  HTTPException
from collections import defaultdict

from fastapi import HTTPException
from crud.test import get_current_user
from crud.test import check_user_permissions

def create_belbin_position(db: Session, data: schema.BelbinPositionRequirementCreate, user_id: str):
    user = check_user_permissions(db, user_id, True)

    if not data.requirements:
        raise HTTPException(status_code=400, detail="No requirements provided")


    # Найти позицию, убедиться, что она принадлежит этому пользователю
    position = db.query(Position).filter(
        Position.id == data.position_id,
        Position.created_by_id == user.id
    ).first()

    if not position:
        raise HTTPException(status_code=403, detail="Not allowed to modify this position")

    # Создать требования
    for req in data.requirements:
        requirement = model.BelbinPositionRequirement(
            position_id=data.position_id,
            role_id=req.role_id,
            min_score=req.min_score,
            is_key=req.is_key
        )
        db.add(requirement)

    db.commit()
    db.refresh(position)
    return {"position_id": data.position_id, "created_count": len(data.requirements)}

def get_belbin_position(db: Session, user_id: str):
    user = check_user_permissions(db, user_id, True)


    results = db.query(
        model.BelbinPositionRequirement,
        Position.title,
        BelbinRole.name,
        BelbinRole.description
    ).join(
        Position, model.BelbinPositionRequirement.position_id == Position.id
    ).join(
        BelbinRole, model.BelbinPositionRequirement.role_id == BelbinRole.id
    ).filter(
        Position.created_by_id == user.id  
    ).all()
    grouped = defaultdict(list)

    for req, title, role_name, role_desc in results:
        grouped[(req.position_id, title)].append({
            "id": req.id,
            "position_id": req.position_id,
            "role_id": req.role_id,
            "min_score": req.min_score,
            "is_key": req.is_key,
            "role_name": role_name,
            "role_description": role_desc
        })

    return [
        {
            "position_id": position_id,
            "position_title": title,
            "requirements": requirements
        }
        for (position_id, title), requirements in grouped.items()
    ]

def delete_belbin_position(db: Session, position_id: int, user_id: str):
    user = check_user_permissions(db, user_id, True)

    position = db.query(Position).filter(
        Position.id == position_id,
        Position.created_by_id == user.id
    ).first()

    if not position:
        raise HTTPException(status_code=403, detail="Not allowed to delete this position")

    positions = db.query(model.BelbinPositionRequirement).filter(
        model.BelbinPositionRequirement.position_id == position_id
    ).all()

    for belbin_position in positions:
        db.delete(belbin_position)

    db.commit()
    return position

def update_belbin_position(db: Session, data: schemas.BelbinPositionRequirement, user_id: str):
    user = check_user_permissions(db, user_id, True)

    position = db.query(Position).filter(
        Position.id == data.position_id,
        Position.created_by_id == user.id
    ).first()
    if not position:
        raise HTTPException(status_code=403, detail="Not allowed to update this position")

    for req_data in data.requirements:
        if req_data.id is None:
            requirement = model.BelbinPositionRequirement(
            position_id=data.position_id,
            role_id=req_data.role_id,
            min_score=req_data.min_score,
            is_key=req_data.is_key
        )
            db.add(requirement)
            continue

        requirement = db.query(model.BelbinPositionRequirement).filter_by(id=req_data.id).first()
        if not requirement:
            raise HTTPException(status_code=404, detail=f"Requirement with id={req_data.id} not found")

        requirement.role_id = req_data.role_id
        requirement.min_score = req_data.min_score
        requirement.is_key = req_data.is_key
        requirement.position_id = req_data.position_id


    db.commit()
    return {"message": "Belbin requirements updated", "position_id": data.position_id}



def create_belbin_role(db: Session, role: schema.BelbinRoleCreate, user_id: str) -> model.BelbinRole:
    user = check_user_permissions(db, user_id, True)
    
    db_role = model.BelbinRole(name=role.name, description=role.description, created_by_id=user.id)
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role


def get_belbin_roles(db: Session, user_id: str):
    user = check_user_permissions(db, user_id, True)
    roles = db.query(BelbinRole).filter(BelbinRole.created_by_id == user.id).all()
    return roles


def update_belbin_role(db: Session, role_id: int, role_data: schema.BelbinRoleCreate, user_id: str):
    user = check_user_permissions(db, user_id, True)

    role = db.query(model.BelbinRole).filter(model.BelbinRole.id == role_id).join(BelbinRole.created_by).filter(Employee.created_by_id == user.id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    role.name = role_data.name
    role.description = role_data.description
    db.commit()
    db.refresh(role)
    return role


def delete_belbin_role(db: Session, role_id: int, user_id: str):
    user = check_user_permissions(db, user_id, True)

    role = db.query(model.BelbinRole).filter(model.BelbinRole.id == role_id).join(BelbinRole.created_by).filter(Employee.created_by_id == user.id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    db.delete(role)
    db.commit()
    return role

def delete_belbin_requiriment(db: Session, requiriment_id: int, user_id: str):
    user = check_user_permissions(db, user_id, True)

    requiriment = db.query(model.BelbinPositionRequirement).filter(model.BelbinPositionRequirement.id == requiriment_id)
    requiriment.delete()
    db.commit()
    return requiriment

# def evaluate_test(db: Session, test_id: int):
    # Получаем тест и ответы
    # test = db.query(models.Test).filter(models.Test.id == test_id).first()
    # if not test:
    #     return None

    # # Получаем требования для должности сотрудника
    # employee = db.query(models.Employee).filter(models.Employee.id == test.employee_id).first()
    # requirements = db.query(models.BelbinPositionRequirement).filter(
    #     models.BelbinPositionRequirement.position_id == employee.position_id
    # ).all()

    # # Вычисляем баллы по ролям
    # role_scores = {}
    # for answer in test.answers:
    #     question = db.query(models.BelbinQuestion).filter(
    #         models.BelbinQuestion.id == answer.question_id
    #     ).first()
    #     role_id = question.role_id
    #     role_scores[role_id] = role_scores.get(role_id, 0) + answer.score

    # # Нормализуем баллы (сумма по блокам = 10, всего 7 блоков -> max 70)
    # total_possible = 70
    # results = []
    # key_roles_met = 0
    # total_key_roles = 0

    # for req in requirements:
    #     role_score = role_scores.get(req.role_id, 0)
    #     normalized_score = (role_score / total_possible) * 100
    #     meets_requirement = normalized_score >= req.min_score

    #     if req.is_key:
    #         total_key_roles += 1
    #         if meets_requirement:
    #             key_roles_met += 1

    #     db_result = models.BelbinTestResult(
    #         test_id=test_id,
    #         role_id=req.role_id,
    #         total_score=normalized_score,
    #         is_required=req.is_key,
    #         meets_requirement=meets_requirement
    #     )
    #     db.add(db_result)
    #     results.append(db_result)

    # # Определяем общий результат
    # if total_key_roles == 0:
    #     overall_result = "high"
    # else:
    #     ratio = key_roles_met / total_key_roles
    #     if ratio >= 0.8:
    #         overall_result = "high"
    #     elif ratio >= 0.5:
    #         overall_result = "medium"
    #     else:
    #         overall_result = "low"

    # test.completed_at = datetime.utcnow()
    # db.commit()

    # return {
    #     "test_id": test_id,
    #     "employee_id": test.employee_id,
    #     "overall_result": overall_result,
    #     "results": results
    # }


def get_test_results(db: Session, test_id: int):
    test = db.query(models.Test).filter(models.Test.id == test_id).first()
    if not test:
        return None

    results = db.query(models.BelbinTestResult).filter(
        models.BelbinTestResult.test_id == test_id
    ).all()

    return results