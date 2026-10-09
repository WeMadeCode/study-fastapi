"""L6 练习：第一次真实 embedding——验证模型可用性,拿到向量维度,亲眼看向量的语义性。"""

import asyncio
import math

from app.services.llm.client import llm_client


def cosine(a: list[float], b: list[float]):
    """余弦相似度：值越接近1，两向量夹角越小，语义越近。"""
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    return dot / (norm_a * norm_b)


async def main():
    vectors = await llm_client.embed(
        [
            "怎么申请退货退款?",
            "退换货的流程是什么?",
            "今天北京天气晴,气温二十四度。",
        ]
    )
    v1, v2, v3 = vectors
    print(f"向量维度: {len(v1)}")
    print(f"前 8 个分量: {[round(x, 4) for x in v1[:8]]}")
    print(f"同义两问相似度: {cosine(v1, v2):.4f}")
    print(f"无关两问相似度: {cosine(v1, v3):.4f}")


if __name__ == "__main__":
    asyncio.run(main())
