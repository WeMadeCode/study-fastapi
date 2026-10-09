"""L6 练习：检索——问题文本 → 向量 → pgvector 余弦距离 top-k。"""

import asyncio

from sqlalchemy import select

from app.database.pgsql_client import AsyncSessionLocal
from app.models import EmbeddingChunk, News
from app.services.llm.client import llm_client

TOP_K = 3


async def search(question: str, top_k: int = TOP_K):
    # 1. 问题 → 向量。embed 的入参是列表,单条查询也传列表,取 [0]
    query_vec = (await llm_client.embed([question]))[0]

    # 2. cosine_distance() 就是 <=> 操作符,距离 = 1 - 余弦相似度,越小越相似
    distance = EmbeddingChunk.embedding.cosine_distance(query_vec).label("distance")

    async with AsyncSessionLocal() as session:
        stmt = (
            select(EmbeddingChunk, News.title, distance)
            .join(News, EmbeddingChunk.news_id == News.id)
            .order_by(distance)
            .limit(top_k)
        )
        rows = (await session.execute(stmt)).all()

        print(f"问题：{question}")
        for chunk, title, dist in rows:
            print(f"  [{dist:.4f}] {title} #chunk{chunk.chunk_index}")
            print(f"           {chunk.content[:48]}…")


async def compare_operators(question: str):
    """加餐：同一问题,三种距离算法的 top-3 对比。"""
    query_vec = (await llm_client.embed([question]))[0]

    operators = [
        ("cosine <=>", EmbeddingChunk.embedding.cosine_distance(query_vec)),
        ("l2     <->", EmbeddingChunk.embedding.l2_distance(query_vec)),
        ("inner  <#>", EmbeddingChunk.embedding.max_inner_product(query_vec)),
    ]

    async with AsyncSessionLocal() as session:
        for name, expr in operators:
            stmt = select(EmbeddingChunk.chunk_index, expr).order_by(expr).limit(TOP_K)
            rows = (await session.execute(stmt)).all()
            scores = "  ".join(f"chunk{i}={score:.4f}" for i, score in rows)
            print(f"  {name}: {scores}")


async def main() -> None:
    # 语义相关但零字面重叠——期望命中「向量检索原理」
    await search("怎么让机器按意思找内容")
    print("=" * 60)
    # 无关问题——期望距离明显变大
    await search("今天股票行情如何")
    print("=" * 60)
    await compare_operators("怎么让机器按意思找内容")


if __name__ == "__main__":
    asyncio.run(main())
