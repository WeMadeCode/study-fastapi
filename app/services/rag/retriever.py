"""RAG 检索:问题向量 → pgvector 余弦距离 top-k。

约定与 crud 一致:收 AsyncSession,只做查询(SELECT 只读,不 commit);
embedding 调用不属于本模块——调用方先把问题转成向量再进来。
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EmbeddingChunk, News

TOP_K = 3
MAX_DISTANCE = 0.5  # 余弦距离阈值：超过视为不相关，宁可不检索


async def search_similar_chunks(
    db: AsyncSession,
    query_vec: list[float],
    top_k: int = TOP_K,
    max_distance: float = MAX_DISTANCE,
):
    """余弦距离升序取 top-k。

    返回 (标题, 块内容, 距离) 三元组列表,已按 max_distance 过滤(距离越小越相似)。
    调参时把过滤条件临时去掉,就能看到全量 top-k 的距离分布。
    """
    distance = EmbeddingChunk.embedding.cosine_distance(query_vec).label("distance")

    stmt = (
        select(News.title, EmbeddingChunk.content, distance)
        .join(News, EmbeddingChunk.news_id == News.id)
        .order_by(distance)
        .limit(top_k)
    )

    rows = (await db.execute(stmt)).all()

    return [(title, content, dist) for title, content, dist in rows if dist <= max_distance]
