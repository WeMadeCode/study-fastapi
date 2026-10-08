"""Alembic 的"点名册":显式导入所有模型,让它们注册进 Base.metadata。"""

from .category import Category
from .conversations import Conversation
from .embedding import EmbeddingChunk
from .favorite import Favorite
from .history import History
from .messages import Message
from .news import News
from .posts import Post
from .users import User

__all__ = ["Favorite", "Category", "History", "News", "Post", "User", "Conversation", "Message", "EmbeddingChunk"]
