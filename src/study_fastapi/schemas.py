from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=50)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    name: str | None = None
    is_active: bool | None = None


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    is_active: bool
    created_at: datetime
