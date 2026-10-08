from datetime import datetime

from pgvector.psycopg import register_vector_async
from sqlalchemy import DateTime, event
from sqlalchemy.dialects.postgresql.psycopg import AsyncAdapt_psycopg_connection
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import ConnectionPoolEntry

from app.config.config import settings

async_engine = create_async_engine(settings.database_url, echo=settings.debug)

AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)


class Base(DeclarativeBase):
    create_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    update_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )


async def get_async_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

"""
1.为什么挂 sync_engine：create_async_engine 返回的 AsyncEngine 是个门面，
真正的连接池挂在它底层的同步引擎上。所有「每个物理连接建立时要做的事」都必须通过 
event.listens_for(engine.sync_engine, "connect")——这是 async 引擎的通用模式，
以后配置任何驱动级钩子都是这个写法。

2. 为什么有 run_async：psycopg3 的连接在 SQLAlchemy 的 greenlet 桥里以同步外观出现，
run_async 是它执行 async 函数的通道（register_vector_async 本身是 async 函数）。

3. 不注册会怎样：你传进去的 list[float] 会以 text 类型发给 Postgres，
Postgres 拒绝 text→vector 隐式转换，
插入报 column is of type vector but expression is of type text。
注册后参数带 vector 的 OID 发送、查询结果被解析成 pgvector.Vector 对象。
（此写法来自 pgvector-python 官方 README 的 SQLAlchemy + psycopg 异步示例。）
"""
@event.listens_for(async_engine.sync_engine, "connect")
def register_pgvector(dbapi_connection: AsyncAdapt_psycopg_connection, connection_record: ConnectionPoolEntry):
    dbapi_connection.run_async(register_vector_async)
