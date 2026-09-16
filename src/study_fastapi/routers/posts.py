from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from study_fastapi import crud, schemas
from study_fastapi.database import get_db

#  帖子围绕用户展开，所以创建、列表挂嵌套路径，全局列表用根路径
router = APIRouter(tags=["posts"])


@router.post(
    "/user/{user_id}/posts",
    response_model=schemas.PostPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_post_for_user(
    user_id: int,
    post_in: schemas.PostCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    user = crud.get_user(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return crud.create_post(db, user, post_in)


@router.get("/user/{user_id}/posts", response_model=list[schemas.PostPublic])
def list_posts_for_user(user_id: int, db: Session = Depends(get_db)):  # noqa: B008
    user = crud.get_user(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return crud.get_user_posts(db, user)
