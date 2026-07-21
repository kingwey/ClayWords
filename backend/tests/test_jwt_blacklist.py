"""JWT 黑名单单元测试

覆盖路径：
- create_access_token / create_refresh_token 都写入 jti
- revoke_token: 计算 TTL = exp - now，写入 Redis
- is_token_revoked: 未撤销 → False；撤销后 → True
- legacy token（无 jti）revoke/check 静默处理不抛异常
- get_current_user: 黑名单 token → 401 "Token has been revoked"
- logout: 读 cookie → revoke 两个 token → 清 cookie
"""

from __future__ import annotations

from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jose import jwt

from app.core.config import settings
from app.services.auth import (
    create_access_token,
    create_refresh_token,
    is_token_revoked,
    revoke_token,
    verify_token,
)


# ---- 辅助 ------------------------------------------------------------------


def _decode_raw(token: str) -> dict:
    """不校验签名地解码 payload（测试用）。"""
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"verify_exp": False},
    )


# ---- jti 写入 --------------------------------------------------------------


@pytest.mark.unit
def test_access_token_contains_jti():
    token = create_access_token({"sub": "u-1", "role": "user"})
    payload = _decode_raw(token)
    assert "jti" in payload
    assert len(payload["jti"]) == 32  # uuid4().hex


@pytest.mark.unit
def test_refresh_token_contains_jti():
    token = create_refresh_token({"sub": "u-1"})
    payload = _decode_raw(token)
    assert "jti" in payload


@pytest.mark.unit
def test_two_tokens_have_different_jtis():
    t1 = create_access_token({"sub": "u-1"})
    t2 = create_access_token({"sub": "u-1"})
    assert _decode_raw(t1)["jti"] != _decode_raw(t2)["jti"]


# ---- revoke_token ----------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_revoke_token_sets_redis_key_with_ttl():
    token = create_access_token({"sub": "u-1"})
    jti = _decode_raw(token)["jti"]

    stored: dict = {}

    async def fake_set(key: str, value: str, ex: Optional[int] = None):
        stored[key] = (value, ex)

    mock_redis = MagicMock()
    mock_redis.set = fake_set
    mock_redis.get = AsyncMock(return_value=None)

    with patch("app.core.redis.redis_client", mock_redis):
        await revoke_token(token)

    key = f"revoked:jti:{jti}"
    assert key in stored
    value, ttl = stored[key]
    assert value == "1"
    assert ttl is not None and ttl > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_revoke_invalid_token_is_noop():
    """签名无效的 token 不应抛异常——logout 时 cookie 被篡改不应让接口 500。"""
    await revoke_token("not.a.valid.token")  # must not raise


@pytest.mark.unit
@pytest.mark.asyncio
async def test_revoke_legacy_token_without_jti_is_noop():
    """没有 jti 的老 token 无法加入黑名单，静默跳过即可。"""
    # 手工造一个没有 jti 的 token
    from datetime import timedelta
    from app.core.time import utcnow
    raw = jwt.encode(
        {"sub": "u-1", "type": "access", "exp": utcnow() + timedelta(minutes=10)},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    # 不应抛异常
    await revoke_token(raw)


# ---- is_token_revoked ------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_is_token_revoked_returns_false_when_not_in_redis():
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=None)

    with patch("app.core.redis.redis_client", mock_redis):
        assert await is_token_revoked("some-jti") is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_is_token_revoked_returns_true_when_in_redis():
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value="1")

    with patch("app.core.redis.redis_client", mock_redis):
        assert await is_token_revoked("some-jti") is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_is_token_revoked_returns_false_for_none_jti():
    """无 jti 的旧 token 不视为撤销（否则所有旧 token 都会被拒）。"""
    assert await is_token_revoked(None) is False


# ---- 整合：revoke → check --------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_revoke_then_check_round_trip():
    """同一个 jti：revoke 后 is_revoked 应返回 True。"""
    token = create_access_token({"sub": "u-1"})
    jti = _decode_raw(token)["jti"]

    store: dict = {}

    async def fake_set(key, value, ex=None):
        store[key] = value

    async def fake_get(key):
        return store.get(key)

    mock_redis = MagicMock()
    mock_redis.set = fake_set
    mock_redis.get = fake_get

    with patch("app.core.redis.redis_client", mock_redis):
        assert await is_token_revoked(jti) is False
        await revoke_token(token)
        assert await is_token_revoked(jti) is True


# ---- get_current_user 黑名单检查 -------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_current_user_rejects_revoked_token():
    """已撤销的合法 token 应 401 "Token has been revoked"。"""
    from fastapi import HTTPException
    from app.api.auth import get_current_user
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

    from app.models.entities import Base

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    token = create_access_token({"sub": "u-1", "role": "user"})

    with patch("app.api.auth.is_token_revoked", AsyncMock(return_value=True)):
        async with maker() as session:
            with pytest.raises(HTTPException) as exc:
                await get_current_user(access_token=token, session=session)

    assert exc.value.status_code == 401
    assert "revoked" in exc.value.detail.lower()

    await engine.dispose()


# ---- logout 撤销两个 token -------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_logout_revokes_both_tokens():
    """logout 必须把 access + refresh 都加入黑名单，不只是删 cookie。"""
    from fastapi import Response
    from app.api.auth import logout

    access = create_access_token({"sub": "u-1", "role": "user"})
    refresh = create_refresh_token({"sub": "u-1"})

    revoked: list[str] = []

    async def fake_revoke(token: str):
        revoked.append(token)

    with patch("app.api.auth.revoke_token", side_effect=fake_revoke):
        await logout(response=Response(), access_token=access, refresh_token=refresh)

    assert access in revoked
    assert refresh in revoked


@pytest.mark.unit
@pytest.mark.asyncio
async def test_logout_without_cookies_does_not_crash():
    """没有 cookie 的 logout 请求（已过期或浏览器清空）不应 500。"""
    from fastapi import Response
    from app.api.auth import logout

    with patch("app.api.auth.revoke_token", AsyncMock()):
        result = await logout(response=Response(), access_token=None, refresh_token=None)

    assert result["message"] == "Logged out successfully"
