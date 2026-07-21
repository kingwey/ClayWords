"""Database Session Management"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import settings
from app.models.entities import Base


logger = structlog.get_logger()


def _normalize_db_url(url: str) -> tuple[str, dict]:
    """规范化数据库 URL 为 asyncpg 驱动，并返回连接参数。

    - Render 的 connectionString 形如 postgres://... / postgresql://...，
      SQLAlchemy 异步引擎需要显式异步驱动 postgresql+asyncpg://...。
    - 托管 PG（Neon / Supabase 等）常在 URL 里带 libpq 的 sslmode /
      channel_binding 查询参数，asyncpg 不识别，需剥离并改用 connect_args 传 SSL。
    """
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]

    connect_args: dict = {}
    parts = urlsplit(url)
    if parts.query:
        kept, needs_ssl = [], False
        for k, v in parse_qsl(parts.query, keep_blank_values=True):
            if k == "sslmode":
                needs_ssl = v not in ("disable", "")
                continue
            if k == "channel_binding":
                continue
            kept.append((k, v))
        if needs_ssl:
            connect_args["ssl"] = True
        url = urlunsplit(
            (parts.scheme, parts.netloc, parts.path, urlencode(kept), parts.fragment)
        )
    return url, connect_args


_db_url, _db_connect_args = _normalize_db_url(settings.DATABASE_URL)

# 连接池：默认 5/10 在 SSE 长连接 + 多副本下偏小，参数化后便于按环境调整
# 同时设置 pool_recycle 防止 PG 服务端 idle 超时杀连接，pool_pre_ping 在网络抖动时校验
engine = create_async_engine(
    _db_url,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    connect_args=_db_connect_args,
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
