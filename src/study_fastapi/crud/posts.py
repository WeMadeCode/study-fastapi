from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from study_fastapi.models import post, user
from study_fastapi.schemas.post import PostCreate


async def create_post(db: AsyncSession, user: user.User, post_in: PostCreate):
    model = post.Post(**post_in.model_dump(), author=user)

    db.add(model)
    await db.commit()
    await db.refresh(model)
    return model


async def get_user_posts(db: AsyncSession, user: user.User):
    result = select(post.Post).where(post.Post.user_id == user.id)
    return list(await db.scalars(result))
