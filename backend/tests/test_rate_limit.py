"""速率限制中间件单元测试

通过 fakeredis 模拟 Redis 服务端，验证滑动窗口的关键不变量。
使用 httpx.AsyncClient 直接走 ASGI，避免 TestClient 每请求新建 event loop
导致的 fakeredis Future 跨 loop 绑定错误。
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI

from app.core.rate_limit import RateLimitMiddleware, RateLimitRule


@pytest.fixture
async def fake_redis(monkeypatch):
    """用 fakeredis 替换 redis_client._client，并按测试函数 loop 创建。"""
    fakeredis = pytest.importorskip("fakeredis")
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)

    from app.core import redis as redis_mod

    monkeypatch.setattr(redis_mod.redis_client, "_client", fake, raising=False)
    yield fake
    await fake.aclose()


def _make_app(rules: dict[str, RateLimitRule]) -> FastAPI:
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, rules=rules)

    @app.get("/api/v1/auth/login")
    def login():
        return {"ok": True}

    @app.post("/api/v1/orders")
    def create_order():
        return {"ok": True}

    @app.get("/api/v1/health")
    def health():
        return {"ok": True}

    return app


async def _async_client(app: FastAPI):
    """构造一个绑定 ASGI 的 httpx 客户端，避免 TestClient 多 loop 问题。"""
    import httpx

    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_under_limit_passes(fake_redis):
    rules = {"/api/v1/auth/login": RateLimitRule(3, 60, "ip")}
    app = _make_app(rules)
    async with await _async_client(app) as ac:
        for i in range(3):
            r = await ac.get("/api/v1/auth/login")
            assert r.status_code == 200, f"#{i} should pass"
            assert int(r.headers["X-RateLimit-Remaining"]) == 3 - (i + 1)


@pytest.mark.asyncio
async def test_over_limit_returns_429(fake_redis):
    rules = {"/api/v1/auth/login": RateLimitRule(2, 60, "ip")}
    app = _make_app(rules)
    async with await _async_client(app) as ac:
        await ac.get("/api/v1/auth/login")
        await ac.get("/api/v1/auth/login")
        r = await ac.get("/api/v1/auth/login")
        assert r.status_code == 429
        assert r.headers["Retry-After"] == "60"
        assert r.headers["X-RateLimit-Remaining"] == "0"


@pytest.mark.asyncio
async def test_different_ips_independent(fake_redis):
    rules = {"/api/v1/auth/login": RateLimitRule(1, 60, "ip")}
    app = _make_app(rules)
    async with await _async_client(app) as ac:
        r1 = await ac.get(
            "/api/v1/auth/login", headers={"X-Forwarded-For": "1.2.3.4"}
        )
        r2 = await ac.get(
            "/api/v1/auth/login", headers={"X-Forwarded-For": "5.6.7.8"}
        )
        assert r1.status_code == 200
        assert r2.status_code == 200, "不同 IP 应独立计数"


@pytest.mark.asyncio
async def test_anonymous_user_scope_skips(fake_redis):
    """user 作用域规则在没有 token 时应跳过限流。"""
    rules = {"/api/v1/orders": RateLimitRule(1, 60, "user")}
    app = _make_app(rules)
    async with await _async_client(app) as ac:
        for _ in range(5):
            r = await ac.post("/api/v1/orders")
            assert r.status_code == 200


@pytest.mark.asyncio
async def test_unrelated_path_not_limited(fake_redis):
    rules = {"/api/v1/auth/login": RateLimitRule(1, 60, "ip")}
    app = _make_app(rules)
    async with await _async_client(app) as ac:
        await ac.get("/api/v1/auth/login")
        for _ in range(5):
            r = await ac.get("/api/v1/health")
            assert r.status_code == 200


@pytest.mark.asyncio
async def test_window_rolls_over(fake_redis):
    """1 秒窗口下，等过窗口后应恢复。"""
    rules = {"/api/v1/auth/login": RateLimitRule(1, 1, "ip")}
    app = _make_app(rules)
    async with await _async_client(app) as ac:
        r1 = await ac.get("/api/v1/auth/login")
        r2 = await ac.get("/api/v1/auth/login")
        assert r1.status_code == 200
        assert r2.status_code == 429

        await asyncio.sleep(1.2)
        r3 = await ac.get("/api/v1/auth/login")
        assert r3.status_code == 200, "窗口滚动后应恢复"


@pytest.mark.asyncio
async def test_redis_failure_fails_open(monkeypatch):
    """Redis 不可达时应放行（fail-open）。"""
    from app.core.rate_limit import RedisRateLimiter
    from app.core import redis as redis_mod

    class _BrokenRaw:
        async def evalsha(self, *a, **kw):
            raise ConnectionError("redis down")

        async def script_load(self, *a, **kw):
            raise ConnectionError("redis down")

    monkeypatch.setattr(redis_mod.redis_client, "_client", _BrokenRaw(), raising=False)

    limiter = RedisRateLimiter()
    limiter._sha = "fake-sha"  # 跳过 script_load，直接 evalsha 失败

    rule = RateLimitRule(1, 60, "ip")
    current, allowed = await limiter.check("rl:test", rule, "m1")
    assert allowed is True, "Redis 故障应 fail-open"
    assert current == 0
