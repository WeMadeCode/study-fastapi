from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from study_fastapi import models, schemas


def create_user(db: Session, user_in: schemas.UserCreate):
    user = models.User(**user_in.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_email(db: Session, email: str):
    result = select(models.User).where(models.User.email == email)
    return db.scalar(result)


def get_user(db: Session, user_id: int):
    return db.get(models.User, user_id)


def get_users(db: Session, skip: int = 0, limit: int = 100):
    sel = (
        select(models.User)
        .options(selectinload(models.User.posts))
        .offset(skip)
        .limit(limit)
    )

    result = db.scalars(sel)
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


def create_post(db: Session, user: models.User, post_in: schemas.PostCreate):
    post = models.Post(**post_in.model_dump(), author=user)

    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def get_user_posts(db: Session, user: models.User):
    result = select(models.Post).where(models.Post.user_id == user.id)
    return list(db.scalars(result))
