from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from study_fastapi.models import Category


async def list_categories(db: AsyncSession):
    stmt = select(Category).order_by(Category.sort_order)
    return list(await db.scalars(stmt))
