from pgvector.sqlalchemy import VECTOR
from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.pgsql_client import Base


class EmbeddingChunk(Base):
    __tablename__ = "embedding_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="块ID")
    news_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("news.id", ondelete="CASCADE"), nullable=False, comment="所属新闻ID"
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, comment="块序号")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="块序号")
    embedding: Mapped[list[float]] = mapped_column(VECTOR(1024), nullable=False, comment="1024维语义向量")

    def __repr__(self) -> str:
        return f"<EmbeddingChunk(id={self.id}, news_id={self.news_id}, chunk_index={self.chunk_index})>"
