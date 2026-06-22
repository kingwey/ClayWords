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
