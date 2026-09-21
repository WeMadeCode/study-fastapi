from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from study_fastapi.crud import users
from study_fastapi.database.pgsql_client import get_async_db
from study_fastapi.schemas.user import UserCreate, UserPublic, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_async_db),  # noqa: B008
):
    if await users.get_user_by_email(db, user_in.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )
    try:
        return await users.create_user(db, user_in)
    except InterruptedError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )


@router.get("", response_model=list[UserPublic])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),  # noqa: B008
):
    return await users.get_users(db, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserPublic)
async def read_user(user_id: int, db: AsyncSession = Depends(get_async_db)):  # noqa: B008
    item = await users.get_user_with_posts(db, user_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return item


@router.patch("/{user_id}", response_model=UserPublic)
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_async_db),  # noqa: B008
):
    item = await users.get_user_with_posts(db, user_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return await users.update_user(db, item, user_in)


@router.delete("/user_id", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_async_db)):  # noqa: B008
    item = await users.get_user_with_posts(db, user_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    await users.delete_user(db, item)
