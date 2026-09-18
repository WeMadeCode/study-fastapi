from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from study_fastapi import models, schemas


async def create_user(db: AsyncSession, user_in: schemas.UserCreate):
    user = models.User(**user_in.model_dump())
    db.add(user)
    await db.commit()
    # refresh 时顺便把 posts 关系也加载了(新用户必然是空列表,但不加载 = 序列化爆炸)
    await db.refresh(user, attribute_names=["posts"])
    return user


async def get_user_by_email(db: AsyncSession, email: str):
    result = select(models.User).where(models.User.email == email)
    return await db.scalar(result)


async def get_user(db: AsyncSession, user_id: int):
    return await db.get(models.User, user_id)


async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100):
    sel = (
        select(models.User)
        .options(selectinload(models.User.posts))
        .offset(skip)
        .limit(limit)
    )
    result = await db.scalars(sel)
    return list(result)


async def update_user(db: AsyncSession, user: models.User, user_in: schemas.UserUpdate):
    for key, value in user_in.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, user: models.User):
    await db.delete(user)
    await db.commit()


async def create_post(db: AsyncSession, user: models.User, post_in: schemas.PostCreate):
    post = models.Post(**post_in.model_dump(), author=user)

    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


async def get_user_posts(db: AsyncSession, user: models.User):
    result = select(models.Post).where(models.Post.user_id == user.id)
    return list(await db.scalars(result))


async def get_user_with_posts(db: AsyncSession, user_id: int):
    """用户 + 帖子一起取(异步世界必须显式加载关联)。"""
    return await db.scalar(
        select(models.User)
        .options(selectinload(models.User.posts))
        .where(models.User.id == user_id)
    )
