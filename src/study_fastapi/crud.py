from sqlalchemy import select
from sqlalchemy.orm import Session

from study_fastapi import models, schemas


def create_user(db: Session, user_in: schemas.UserCreate):
    user = models.User(**user_in.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user(db: Session, user_id: int):
    return db.get(models.User, user_id)


def get_users(db: Session, skip: int = 0, limit: int = 100):
    result = db.scalars(select(models.User).offset(skip).limit(limit)).all()
    return list(result)


def update_user(db: Session, user: models.User, user_in: schemas.UserUpdate):
    for key, value in user_in.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: models.User):
    db.delete(user)
    db.commit()
