"""L6 练习：RAG 完整闭环——检索 top-k → 拼 prompt → 模型生成。"""

import asyncio

from openai.types.chat import ChatCompletionMessageParam
from sqlalchemy import select

from app.database.pgsql_client import AsyncSessionLocal
from app.models import EmbeddingChunk, News
from app.services.llm.client import llm_client

TOP_K = 3
MAX_DISTANCE = 0.5  # 距离阈值:超过视为不相关,宁可不检索

SYSTEM_PROMPT_HEAD = """你是一个知识库问答助手。请仅根据下面的参考资料回答用户问题，并在回答末尾用 [资料名] 注明使用了哪些资料。若资料不足以回答，直接回复「知识库中没有相关资料」，不要编造。

参考资料：
"""


async def retrieve(question: str, top_k: int = TOP_K) -> list[tuple[str, str, float]]:
    """检索 top-k 并按距离阈值过滤,返回 (标题, 块内容, 距离) 三元组列表。"""
    query_vec = (await llm_client.embed([question]))[0]
    distance = EmbeddingChunk.embedding.cosine_distance(query_vec).label("distance")

    async with AsyncSessionLocal() as session:
        stmt = (
            select(News.title, EmbeddingChunk.content, distance)
            .join(News, EmbeddingChunk.news_id == News.id)
            .order_by(distance)
            .limit(top_k)
        )
        rows = (await session.execute(stmt)).all()

    hits = [(title, content, dist) for title, content, dist in rows if dist <= MAX_DISTANCE]
    for title, _content, dist in rows:
        if dist > MAX_DISTANCE:
            print(f"  ✗ 超阈值丢弃：{title}（{dist:.4f} > {MAX_DISTANCE}）")
    return hits


def build_context(hits: list[tuple[str, str, float]]) -> str:
    blocks = [f"[{i + 1}] {title}\n{content}" for i, (title, content, _dist) in enumerate(hits)]
    return "\n\n".join(blocks)


async def rag_answer(question: str) -> None:
    print(f"问题：{question}")

    # 1. R：检索 + 过滤
    hits = await retrieve(question)
    print(f"  采纳 {len(hits)} 块资料")
    if not hits:
        print("  没有可用资料,跳过模型调用\n")
        return

    # 2. A：资料拼进 system,问题进 user(字符串拼接,不用 .format)
    context = build_context(hits)
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": SYSTEM_PROMPT_HEAD + context},
        {"role": "user", "content": question},
    ]

    # 3. G：生成
    answer = await llm_client.chat(messages)
    print(f"  回答：{answer}\n")


async def main() -> None:
    # 知识库内问题——期望引用资料作答
    await rag_answer("切块太大或太小分别有什么问题?")
    print("=" * 60)
    # 知识库外问题——期望被阈值拦住,或模型老实说不知道
    await rag_answer("怎么申请无人机执照?")


if __name__ == "__main__":
    asyncio.run(main())
