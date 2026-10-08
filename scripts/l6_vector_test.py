"""L6 练习:向量表读写闭环——随机向量验证 建表→插入→cosine 检索→返回类型,不调 API。"""

import asyncio
import random

from sqlalchemy import select

from app.database.pgsql_client import AsyncSessionLocal
from app.models import Category, EmbeddingChunk, News


async def main():
    fake = [random.random() for _ in range(1024)]

    async with AsyncSessionLocal() as session:
        news_id = (await session.scalars(select(News.id).limit(1))).first()
        if news_id is None:
            category_id = (await session.scalars(select(Category.id).limit(1))).first()
            if category_id is None:
                category = Category(name="测试分类")
                session.add(category)
                await session.flush()
                category_id = category.id
            news = News(title="RAG 测试新闻", content="占位新闻：只为拿到news_id，category_id = category_id")
            session.add(news)
            await session.flush()
            news_id = news.id

        session.add(EmbeddingChunk(news_id=news_id, chunk_index=0, content="退货流程测试块", embedding=fake))
        await session.commit()

        stmt = select(EmbeddingChunk).order_by(EmbeddingChunk.embedding.cosine_distance(fake)).limit(1)
        row = (await session.scalars(stmt)).first()
        if row is not None:
            print("返回类型:", type(row.embedding))
            print("前3维:", list(row.embedding)[:3])
            print("长度:", len(row.embedding))


if __name__ == "__main__":
    asyncio.run(main())
