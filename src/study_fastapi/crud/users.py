from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from study_fastapi.models import users
from study_fastapi.schemas.users import UserCreate, UserUpdate


async def create_user(db: AsyncSession, user_in: UserCreate):
    model = users.User(**user_in.model_dump())
    db.add(model)
    await db.commit()
    await db.refresh(model, attribute_names=["posts"])
    return model


async def get_user_by_email(db: AsyncSession, email: str):
    result = select(users.User).where(users.User.email == email)
    return await db.scalar(result)


async def get_user(db: AsyncSession, user_id: int):
    return await db.get(users.User, user_id)


async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100):
    sel = (
        select(users.User)
        .options(selectinload(users.User.posts))
        .offset(skip)
        .limit(limit)
    )
    result = await db.scalars(sel)
    return list(result)


async def update_user(db: AsyncSession, user: users.User, user_in: UserUpdate):
    for key, value in user_in.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, user: users.User):
    await db.delete(user)
    await db.commit()


async def get_user_with_posts(db: AsyncSession, user_id: int):
    """用户 + 帖子一起取(异步世界必须显式加载关联)。"""
    return await db.scalar(
        select(users.User)
        .options(selectinload(users.User.posts))
        .where(users.User.id == user_id)
    )
