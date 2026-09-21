from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from study_fastapi.cache import news_cache
from study_fastapi.crud import categories, news
from study_fastapi.database.pgsql_client import get_async_db
from study_fastapi.database.redis_client import get_redis
from study_fastapi.schemas.categories import CategoryPublic
from study_fastapi.schemas.news import NewsListPublic

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("/categories", response_model=list[CategoryPublic])
async def get_categories(
    db: AsyncSession = Depends(get_async_db),  # noqa: B008
    r: Redis = Depends(get_redis),  # noqa: B008
):
    key = news_cache.build_categories_key()
    cached = await news_cache.get_json_cache(r, key)
    if cached is not None:
        return [CategoryPublic.model_validate(c) for c in cached]

    items = await categories.list_categories(db)
    payload = [CategoryPublic.model_validate(item) for item in items]

    await news_cache.set_json_cache(
        r, key, [p.model_dump(mode="json") for p in payload]
    )

    return payload


@router.get("/list", response_model=NewsListPublic)
async def get_news_list(
    db: AsyncSession = Depends(get_async_db),  # noqa: B008
    r: Redis = Depends(get_redis),  # noqa: B008
    category_id: int = Query(..., alias="categoryId"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, alias="pageSize", ge=1, le=100),
):
    key = news_cache.build_list_key(category_id, page, page_size)

    cached = await news_cache.get_json_cache(r, key)
    if cached is None:
        return NewsListPublic.model_validate(cached)

    items, total = await news.list_news(db, category_id, page, page_size)
    result = NewsListPublic.model_validate({"items": items, "total": total})

    await news_cache.set_json_cache(r, key, result.model_dump(mode="json"))

    return result
