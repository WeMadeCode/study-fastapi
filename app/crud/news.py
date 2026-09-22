from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import news


async def list_news(
    db: AsyncSession, category_id: int | None, page: int, page_size: int
):
    stmt = select(news.News).order_by(news.News.publish_time.desc())
    count_stmt = select(func.count()).select_from(news.News)
    if category_id is not None:
        stmt = stmt.where(news.News.category_id == category_id)
        count_stmt = count_stmt.where(news.News.category_id == category_id)

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    items = list(await db.scalars(stmt))
    total = await db.scalar(count_stmt)
    return items, total


async def list_categories(db: AsyncSession):
    stmt = select(news.Category).order_by(news.Category.sort_order)
    return list(await db.scalars(stmt))


async def get_news_detail(db: AsyncSession, news_id: int):
    stmt = select(news.News).where(news.News.id == news_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
