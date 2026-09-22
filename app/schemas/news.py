from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CategoryPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    sort_order: int


class NewsPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    title: str
    description: str | None
    image: str | None
    author: str | None
    category_id: int
    views: int
    publish_time: datetime


class NewsListPublic(BaseModel):
    items: list[NewsPublic]
    total: int


class NewsDetailPublic(NewsPublic):
    content: str
