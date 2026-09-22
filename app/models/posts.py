from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.pgsql_client import Base

if TYPE_CHECKING:
    from .users import User

class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str]
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    views: Mapped[int] = mapped_column(server_default=text("0"))
    author: Mapped["User"] = relationship(back_populates="posts")
    published: Mapped[bool] = mapped_column(server_default=text("true"))

    def __repr__(self):
        return f"Post(id={self.id},title={self.title},user_id={self.user_id},content={self.content})"
