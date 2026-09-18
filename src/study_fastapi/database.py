from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from study_fastapi.config import settings

from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

async_engine = create_async_engine(settings.database_url, echo=settings.debug)

AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_async_db():
    """异步版依赖:async with 代替手写 try/finally。"""
    async with AsyncSessionLocal() as db:
        yield db
