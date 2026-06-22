"""Database Session Management"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import settings
from app.models.entities import Base


logger = structlog.get_logger()


# 连接池：默认 5/10 在 SSE 长连接 + 多副本下偏小，参数化后便于按环境调整
# 同时设置 pool_recycle 防止 PG 服务端 idle 超时杀连接，pool_pre_ping 在网络抖动时校验
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Initialize database tables.

    生产/staging 必须走 alembic upgrade head；这里只在开发环境保留 create_all
    以便快速起本地服务。否则会导致 schema 漂移、字段类型与 migration 不一致。
    """
    if not settings.is_development:
        logger.info("init_db_skipped_in_non_dev", environment=settings.ENVIRONMENT)
        return

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("init_db_create_all_done", environment=settings.ENVIRONMENT)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting DB session"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for DB session"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
