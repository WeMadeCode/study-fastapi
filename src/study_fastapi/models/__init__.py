"""Alembic 的"点名册":显式导入所有模型,让它们注册进 Base.metadata。"""

from .category import Category
from .favorite import Favorite
from .history import History
from .news import News
from .posts import Post
from .users import User

__all__ = ["Category", "Favorite", "History", "News", "Post", "User"]
