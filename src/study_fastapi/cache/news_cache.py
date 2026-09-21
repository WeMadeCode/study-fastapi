import json
from typing import Any

from redis.asyncio import Redis

NEWS_LIST_TTL = 60  # 列表缓存存活 60 秒


def build_list_key(category_id: int | None, page: int, page_size: int):
    return f"news:list:{category_id or 0}:{page}:{page_size}"


def build_categories_key():
    return "news:categories"


async def get_json_cache(r: Redis, key: str):
    data = await r.get(key)
    if data is None:
        return None
    return json.loads(data)


async def set_json_cache(r: Redis, key: str, payload: Any, expire: int = NEWS_LIST_TTL):
    await r.set(key, json.dumps(payload, ensure_ascii=False), ex=expire)
