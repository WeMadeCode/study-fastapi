from pydantic import BaseModel, ConfigDict, Field


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
    published: bool
