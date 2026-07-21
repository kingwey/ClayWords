"""Rate Limiting Middleware - Redis-backed sliding window

Phase Q10.1.3 + 后续重构：
- 多副本可用：状态保存在 Redis ZSET（score = 时间戳）
- 原子性：通过单条 Lua 脚本完成"清理过期 + 计数 + 写入"
- 用户作用域不再依赖外部中间件填充 request.state.user_id：
  限流中间件自己解析 Authorization header（仅在命中规则时），
  解析失败/匿名时静默跳过 user 作用域规则
- 响应头：X-RateLimit-Limit/Remaining/Reset，超限走 HTTP 429 + Retry-After
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional

import structlog
from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.redis import redis_client


logger = structlog.get_logger()


@dataclass(frozen=True)
class RateLimitRule:
    """速率限制规则"""

    max_requests: int
    window_seconds: int
    scope: str = "ip"  # ip / user / global


# Lua 脚本：原子滑动窗口
#   KEYS[1] = bucket key
#   ARGV[1] = now_ms
#   ARGV[2] = window_ms
#   ARGV[3] = max_requests
#   ARGV[4] = unique member id
# 返回: {current_count, allowed (1/0)}
_SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]

redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
local current = redis.call('ZCARD', key)
if current >= limit then
    return {current, 0}
end
redis.call('ZADD', key, now, member)
redis.call('PEXPIRE', key, window)
return {current + 1, 1}
"""


class RedisRateLimiter:
    """基于 Redis ZSET 的滑动窗口限流器（多实例安全）。"""

    def __init__(self):
        self._sha: Optional[str] = None

    async def _ensure_loaded(self):
        if self._sha is None:
            try:
                self._sha = await redis_client.raw.script_load(_SLIDING_WINDOW_LUA)
            except Exception as e:
                logger.warning("rate_limit_script_load_failed", error=str(e))
                self._sha = None

    async def check(
        self, bucket_key: str, rule: RateLimitRule, member: str
    ) -> tuple[int, bool]:
        """返回 (当前窗口内请求数, 是否放行)。"""
        now_ms = int(time.time() * 1000)
        window_ms = rule.window_seconds * 1000
        await self._ensure_loaded()

        try:
            if self._sha:
                result = await redis_client.raw.evalsha(
                    self._sha, 1, bucket_key, now_ms, window_ms, rule.max_requests, member
                )
            else:
                result = await redis_client.eval(
                    _SLIDING_WINDOW_LUA, 1, bucket_key, now_ms, window_ms, rule.max_requests, member
                )
        except Exception as e:
            # Redis 不可用时降级放行（避免单点故障引发全站 429）
            logger.warning("rate_limit_redis_unavailable", error=str(e), key=bucket_key)
            return (0, True)

        current = int(result[0])
        allowed = bool(result[1])
        return current, allowed


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis 后端的速率限制中间件。"""

    DEFAULT_RULES: Dict[str, RateLimitRule] = {
        "/api/v1/auth/login": RateLimitRule(5, 60, "ip"),
        "/api/v1/sse/tickets": RateLimitRule(60, 3600, "user"),
        "/api/v1/tasks": RateLimitRule(20, 3600, "user"),
        "/api/v1/orders": RateLimitRule(30, 3600, "user"),
    }

    SKIP_PATHS = {"/health", "/metrics"}

    def __init__(self, app, rules: Optional[Dict[str, RateLimitRule]] = None):
        super().__init__(app)
        self.rules = rules if rules is not None else dict(self.DEFAULT_RULES)
        self.limiter = RedisRateLimiter()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        rule = self._get_rule(request.url.path)
        if not rule:
            return await call_next(request)

        scope_key = self._get_scope_key(request, rule.scope)
        if not scope_key:
            # 匿名访问 user 作用域规则 → 跳过；要拦未登录用户请用 ip 作用域
            return await call_next(request)

        bucket_key = f"rl:{rule.scope}:{request.url.path}:{scope_key}"
        # 唯一 member：避免同毫秒并发请求互相覆盖
        member = f"{int(time.time() * 1000)}-{id(request)}"

        current, allowed = await self.limiter.check(bucket_key, rule, member)

        now = time.time()
        reset_at = int(now + rule.window_seconds)

        if not allowed:
            # 在 BaseHTTPMiddleware 内部 raise HTTPException 不会被 FastAPI 接住，
            # 必须直接返回 Response 才能产出 429。
            body = {
                "detail": {
                    "error": "rate_limit_exceeded",
                    "message": (
                        f"Rate limit exceeded. Max {rule.max_requests} "
                        f"requests per {rule.window_seconds} seconds."
                    ),
                    "retry_after": rule.window_seconds,
                }
            }
            return JSONResponse(
                status_code=429,
                content=body,
                headers={
                    "Retry-After": str(rule.window_seconds),
                    "X-RateLimit-Limit": str(rule.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_at),
                },
            )

        response = await call_next(request)
        remaining = max(0, rule.max_requests - current)
        response.headers["X-RateLimit-Limit"] = str(rule.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_at)
        return response

    def _get_rule(self, path: str) -> Optional[RateLimitRule]:
        if path in self.rules:
            return self.rules[path]
        # 前缀匹配（取最长前缀，避免 /api/v1/orders 命中 /api 类规则）
        best: Optional[tuple[str, RateLimitRule]] = None
        for prefix, rule in self.rules.items():
            if path.startswith(prefix.rstrip("/") + "/") or path == prefix:
                if best is None or len(prefix) > len(best[0]):
                    best = (prefix, rule)
        return best[1] if best else None

    def _get_scope_key(self, request: Request, scope: str) -> Optional[str]:
        if scope == "ip":
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                return forwarded.split(",")[0].strip()
            return request.client.host if request.client else None

        if scope == "user":
            # 优先 request.state（若上游中间件已设置）；否则解析 Authorization
            user_id = getattr(request.state, "user_id", None)
            if user_id:
                return user_id
            return _extract_user_id_from_auth_header(request)

        if scope == "global":
            return "global"

        return None


def _extract_user_id_from_auth_header(request: Request) -> Optional[str]:
    """从 Bearer token 解析 user_id；解析失败返回 None。

    限流前的轻量解码，不做用户存在性校验，那是 endpoint 的事。
    """
    auth = request.headers.get("Authorization") or ""
    if not auth.lower().startswith("bearer "):
        return None
    token = auth.split(" ", 1)[1].strip()
    if not token:
        return None
    try:
        from app.services.auth import verify_token

        payload = verify_token(token, "access")
        return payload.get("sub") if payload else None
    except Exception:
        return None


# ============== 装饰器（保留原 API 兼容性，但实际限流仍走中间件） ==============


def rate_limit(max_requests: int, window_seconds: int, scope: str = "user"):
    """语义性装饰器：把规则附在 endpoint 上，便于扫描/文档化。

    实际限流由 RateLimitMiddleware 统一处理。
    """

    def decorator(func):
        func._rate_limit = RateLimitRule(max_requests, window_seconds, scope)
        return func

    return decorator
