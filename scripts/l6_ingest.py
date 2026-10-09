"""L6 练习：入库管线——news.content → 切块 → embedding → 批量写库(幂等:先清空)。"""

import asyncio

from sqlalchemy import delete, select

from app.database.pgsql_client import AsyncSessionLocal
from app.models import Category, EmbeddingChunk, News
from app.services.llm.client import llm_client
from app.services.rag.chunker import split_text

SEED_NEWS: list[tuple[str, str]] = [
    (
        "豆包是什么",
        "豆包是字节跳动推出的 AI 助手，支持多轮对话、写作、翻译和编程辅助等多种能力。豆包大模型家族包含多个不同尺寸的模型，不同模型在响应速度和能力上限上各有取舍。开发者可以通过火山方舟平台调用这些模型，按 token 计费，也支持私有化部署方案。在日常使用中，豆包可以回答知识类问题、辅助撰写文案，也能结合工具完成查天气、查资料等任务。",
    ),
    (
        "向量检索原理",
        "向量检索是 RAG 系统的核心环节。它把文本转换成高维向量，语义相近的文本在向量空间中的距离也更近。检索时，系统把用户的问题同样转换成向量，然后找出距离最近的若干个文本块。这些块会被填进提示词，帮助模型基于资料回答问题。相比关键词检索，向量检索能理解语义层面的相似，比如“怎么退货”和“退换货流程”会被认为高度相关。",
    ),
    (
        "切块策略",
        "切块策略直接影响检索质量。块太大，一段里混进多个话题，命中后噪音就多。块太小，语义碎片化，单块装不下完整的意思。行业常用的折中是每块三百字左右，相邻块保留一小段重叠，防止关键句正好被切在边界上。",
    ),
]


async def main():
    async with AsyncSessionLocal() as session:
        # 素材不足则注入样文(category 复用已有或新建)
        news_list = (await session.scalars(select(News))).all()
        if len(news_list) < 3:
            category_id = (await session.scalars(select(Category.id).limit(1))).first()
            if category_id is None:
                category = Category(name="AI 学习")
                session.add(category)
                await session.flush()
                category_id = category.id
            for title, content in SEED_NEWS:
                session.add(News(title=title, content=content, category_id=category_id))
            await session.commit()
            news_list = (await session.scalars(select(News))).all()

        # 切块：收集 (news_id, chunk_index, 文本) 三元组
        pairs: list[tuple[int, int, str]] = []
        for news in news_list:
            for i, chunk in enumerate(split_text(news.content)):
                pairs.append((news.id, i, chunk))
        print(f"新闻 {len(news_list)} 条 → 切块 {len(pairs)} 块")

        # 一次批量 embed,顺序与 pairs 严格对应
        vectors = await llm_client.embed([text for _, _, text in pairs])

        # 幂等清空后一次写入:事务里只有 INSERT,没有网络 IO
        await session.execute(delete(EmbeddingChunk))
        for (news_id, chunk_index, content), vec in zip(pairs, vectors, strict=True):
            session.add(EmbeddingChunk(news_id=news_id, chunk_index=chunk_index, content=content, embedding=vec))
        await session.commit()
        print(f"已写入 {len(pairs)} 块")


if __name__ == "__main__":
    asyncio.run(main())
