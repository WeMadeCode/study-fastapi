from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import posts, users
from app.schemas.posts import PostCreate


async def create_post(db: AsyncSession, user: users.User, post_in: PostCreate):
    model = posts.Post(**post_in.model_dump(), author=user)

    db.add(model)
    await db.commit()
    await db.refresh(model)
    return model


async def get_user_posts(db: AsyncSession, user: users.User):
    result = select(posts.Post).where(posts.Post.user_id == user.id)
    return list(await db.scalars(result))
