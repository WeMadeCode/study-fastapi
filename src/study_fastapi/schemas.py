from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class PostCreate(BaseModel):
    """POST /user/{user_id}/posts 的请求体"""

    title: str = Field(min_length=1, max_length=200)
    content: str


class PostPublic(BaseModel):
    """帖子的对外结构"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    user_id: int
    views: int


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
