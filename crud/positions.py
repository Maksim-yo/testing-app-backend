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
    db_position = model.Position(**position.model_dump(), created_by_id=user.id)
    db.add(db_position)
    db.commit()
    db.refresh(db_position)
    return db_position

def update_position(db: Session, position_id:int, position_update: schema.PositionCreate, user_id: str):
    position = get_position(db, position_id, user_id)
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