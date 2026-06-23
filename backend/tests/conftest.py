"""Pytest configuration and fixtures"""

import os
import sys
import asyncio
from pathlib import Path
from typing import AsyncGenerator
import pytest

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Set test environment variables before importing app
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://claywords:claywords_secret@localhost:5432/claywords")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("CRYPTO_PEPPER", "test_pepper_for_testing")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for the entire test session"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def pytest_collection_modifyitems(config, items):
    """凡未显式打标记的用例,默认归入 `unit`。

    背景: CI 跑 `pytest -m "unit"`,但历史上大多数 test_ 函数没加
    `@pytest.mark.unit`,导致 96 个用例只跑出 36 个 —— 覆盖率门槛(70%)
    自然达不到,CI 一直在挂。给所有 test_* 默认补上 `unit` 标记,
    让真实的 96 个用例都进 CI。
    """
    import pytest as _pytest
    for item in items:
        existing = {mark.name for mark in item.iter_markers()}
        # 已显式声明分类的不动(smoke / integration / e2e / slow)
        if existing & {"unit", "smoke", "integration", "e2e", "slow"}:
            continue
        item.add_marker(_pytest.mark.unit)


@pytest.fixture
def mock_metrics():
    """Mock metrics for testing"""
    from app.core.metrics import MetricsRegistry
    return MetricsRegistry()


@pytest.fixture
async def db_session():
    """Provide a database session for testing"""
    from app.db.session import async_session_maker

    async with async_session_maker() as session:
        yield session


@pytest.fixture
async def redis_client():
    """Provide a Redis client for testing"""
    from app.core.redis import RedisClient

    client = RedisClient()
    await client.connect()
    yield client
    await client.disconnect()
