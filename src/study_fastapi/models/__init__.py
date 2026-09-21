"""Alembic 的"点名册":显式导入所有模型,让它们注册进 Base.metadata。"""

from study_fastapi.models.category import Category
from study_fastapi.models.favorite import Favorite
from study_fastapi.models.history import History
from study_fastapi.models.news import News
from study_fastapi.models.post import Post
from study_fastapi.models.user import User

__all__ = ["Category", "Favorite", "History", "News", "Post", "User"]
