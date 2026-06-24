"""JWT Authentication Service"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import settings
from app.core.time import utcnow


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Redis key prefix for revoked tokens
_REVOKED_PREFIX = "revoked:jti:"


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access", "jti": uuid.uuid4().hex})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh", "jti": uuid.uuid4().hex})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    """Verify JWT signature and type. Does NOT check revocation (async; caller must do it)."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != token_type:
            return None
        return payload
    except JWTError:
        return None


async def revoke_token(token: str) -> None:
    """Blacklist a token by its jti until it naturally expires.

    TTL is calculated from the token's own exp claim so the Redis key
    is garbage-collected automatically — no separate cleanup job needed.
    """
    from app.core.redis import redis_client

    payload = verify_token(token, "access") or verify_token(token, "refresh")
    if not payload:
        return  # Already invalid, nothing to blacklist

    jti = payload.get("jti")
    if not jti:
        return  # Legacy token without jti — can't blacklist, silently skip

    exp = payload.get("exp")
    now_ts = int(utcnow().timestamp())
    ttl = max(1, int(exp) - now_ts) if exp else settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60

    await redis_client.set(_REVOKED_PREFIX + jti, "1", ex=ttl)


async def is_token_revoked(jti: Optional[str]) -> bool:
    """Return True if this jti has been blacklisted."""
    if not jti:
        return False  # No jti = old token = not revocable via blacklist
    from app.core.redis import redis_client
    return await redis_client.get(_REVOKED_PREFIX + jti) is not None


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
