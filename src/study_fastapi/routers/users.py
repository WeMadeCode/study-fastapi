from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from study_fastapi import crud, schemas
from study_fastapi.database import get_db

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=schemas.UserPublic, status_code=status.HTTP_201_CREATED)
def create_user(user_in: schemas.UserCreate, db: Session = Depends(get_db)):  # noqa: B008
    if crud.get_user_by_email(db, user_in.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )
    try:
        return crud.create_user(db, user_in)
    except InterruptedError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )


@router.get("", response_model=list[schemas.UserPublic])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):  # noqa: B008
    return crud.get_users(db, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=schemas.UserPublic)
def read_user(user_id: int, db: Session = Depends(get_db)):  # noqa: B008
    user = crud.get_user(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.patch("/{user_id}", response_model=schemas.UserPublic)
def update_user(
    user_id: int,
    user_in: schemas.UserUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    user = crud.get_user(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return crud.update_user(db, user, user_in)


@router.delete("/user_id", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)):  # noqa: B008
    user = crud.get_user(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    crud.delete_user(db, user)
