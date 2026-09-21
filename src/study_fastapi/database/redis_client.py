import redis.asyncio as Redis

from study_fastapi.config.config import settings

redis_client = Redis.from_url(
    settings.redis_url,
    decode_responses=True,
)


async def get_redis():
    return redis_client
