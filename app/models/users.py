from typing import TYPE_CHECKING

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.pgsql_client import Base

if TYPE_CHECKING:
    from .posts import Post


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(50))
    password: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码（加密存储）")
    gender: Mapped[str | None] = mapped_column(
        Enum("male", "female", "unknown", name="gender"),
        comment="性别",
        default="unknown",
    )

    is_active: Mapped[bool] = mapped_column(default=True)
    bio: Mapped[str | None] = mapped_column(String(500))
    posts: Mapped[list["Post"]] = relationship(
        back_populates="author", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"User(id={self.id},email={self.email},name={self.name},is_active={self.is_active},created_at={self.create_at})"
