from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import posts, users
from app.database.pgsql_client import get_async_db
from app.schemas.posts import PostCreate, PostPublic

#  帖子围绕用户展开，所以创建、列表挂嵌套路径，全局列表用根路径
router = APIRouter(tags=["posts"])


@router.post(
    "/users/{user_id}/posts",
    response_model=PostPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_post_for_user(
    user_id: int,
    post_in: PostCreate,
    db: AsyncSession = Depends(get_async_db),  # noqa: B008
):
    user = await users.get_user(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return await posts.create_post(db, user, post_in)


@router.get("/users/{user_id}/posts", response_model=list[PostPublic])
async def list_posts_for_user(user_id: int, db: AsyncSession = Depends(get_async_db)):  # noqa: B008
    user = await users.get_user(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return await posts.get_user_posts(db, user)
