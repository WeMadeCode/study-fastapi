from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .posts import PostPublic


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=50)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    name: str | None = None
    is_active: bool | None = None


class UserPublic(BaseModel):
    """用户的对外结构"""

    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    name: str
    is_active: bool
    created_at: datetime
    posts: list[PostPublic] = []  # 用户名下所有的帖子
