from sqlalchemy.orm import Session
from models import positions as model
from schemas import positions as schema
from fastapi import  HTTPException
from crud.test import check_user_permissions
def get_position(db: Session, position_id: int, user_id: str):
    user = check_user_permissions(db, user_id, True)
    db_position = db.query(model.Position).filter(model.Position.id == position_id).first()
    if not db_position:
        raise HTTPException(status_code=404, detail="Должность не найдена")
    if db_position.created_by_id != user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to get this position.")    
    
    return db_position

def get_positions(db: Session, user_id: str):
    user = check_user_permissions(db, user_id, True)

    return db.query(model.Position).filter(model.Position.created_by_id == user.id).all()

def create_position(db: Session, position: schema.PositionCreate, user_id: str):
    user = check_user_permissions(db, user_id, True)
    
    existing = db.query(model.Position).filter_by(title=position.title).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Должность с именем '{position.title}' уже существует")

    db_position = model.Position(**position.model_dump(), created_by_id=user.id)
    db.add(db_position)
    db.commit()
    db.refresh(db_position)
    return db_position

def update_position(db: Session, position_id: int, position_update: schema.PositionCreate, user_id: str):
    # Проверяем права пользователя (пример функции check_user_permissions, если есть)
    user = check_user_permissions(db, user_id, True)

    # Получаем позицию по id и проверяем, что принадлежит пользователю
    position = (
        db.query(model.Position)
        .filter(model.Position.id == position_id)
        .join(model.Position.created_by)
        .filter(model.Position.created_by_id == user.id)
        .first()
    )

    if not position:
        raise HTTPException(status_code=404, detail="Должность не найдена")

    # Проверка уникальности title (исключая текущую позицию)
    existing = (
        db.query(model.Position)
        .filter(model.Position.title == position_update.title)
        .filter(model.Position.id != position_id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Должность с именем '{position_update.title}' уже существует"
        )

    # Обновляем поля из position_update
    for field, value in position_update.model_dump(exclude_unset=True).items():
        setattr(position, field, value)

    db.commit()
    db.refresh(position)
    return position


def delete_position(db: Session, position_id: int, user_id: str):
    user = check_user_permissions(db, user_id, True)

    db_position = db.query(model.Position).filter(model.Position.id == position_id).first()
    if db_position.created_by_id != user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to delete this position.")
    
    if db_position:
        db.delete(db_position)
        db.commit()
    return db_position