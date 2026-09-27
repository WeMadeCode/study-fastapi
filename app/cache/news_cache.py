import json

from redis.asyncio import Redis

NEWS_LIST_TTL = 60  # 列表缓存存活 60 秒

type Json = None | bool | int | float | str | list[Json] | dict[str, Json]


def build_list_key(category_id: int | None, page: int, page_size: int):
    return f"news:list:{category_id or 0}:{page}:{page_size}"


def build_detail_key(news_id: int):
    return f"news:detail:{news_id}"


def build_categories_key():
    return "news:categories"


async def get_json_cache(r: Redis, key: str):
    data = await r.get(key)
    if data is None:
        return None
    return json.loads(data)


async def set_json_cache(r: Redis, key: str, payload: Json, expire: int = NEWS_LIST_TTL):
    await r.set(key, json.dumps(payload, ensure_ascii=False), ex=expire)
