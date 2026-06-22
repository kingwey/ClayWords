"""Rate Limiting Middleware - Phase Q10.1.3"""

import time
from typing import Callable, Dict, Optional
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
from dataclasses import dataclass, field
import asyncio


@dataclass
class RateLimitRule:
    """速率限制规则"""
    max_requests: int  # 最大请求数
    window_seconds: int  # 时间窗口（秒）
    scope: str = "ip"  # 限制范围：ip / user / global


@dataclass
class RateLimitBucket:
    """令牌桶"""
    requests: list = field(default_factory=list)  # [(timestamp, count)]

    def add_request(self, now: float):
        """添加请求"""
        self.requests.append(now)

    def get_count(self, now: float, window: int) -> int:
        """获取时间窗口内的请求数"""
        cutoff = now - window
        # 清理过期记录
        self.requests = [ts for ts in self.requests if ts > cutoff]
        return len(self.requests)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """API 速率限制中间件

    Phase Q10.1.3: 速率限制
    - 登录: 5 次/分钟/IP
    - SSE 票据: 60 次/小时/用户
    - 生成任务: 20 次/小时/用户
    """

    def __init__(self, app):
        super().__init__(app)

        # 存储桶: {(scope, key, endpoint): RateLimitBucket}
        self.buckets: Dict[tuple, RateLimitBucket] = defaultdict(RateLimitBucket)

        # 速率限制规则
        self.rules = {
            # 登录限制
            "/api/v1/auth/login": RateLimitRule(
                max_requests=5,
                window_seconds=60,
                scope="ip"
            ),
            # SSE 票据限制
            "/api/v1/sse/tickets": RateLimitRule(
                max_requests=60,
                window_seconds=3600,
                scope="user"
            ),
            # 任务创建限制（通用）
            "/api/v1/tasks": RateLimitRule(
                max_requests=20,
                window_seconds=3600,
                scope="user"
            ),
            # 订单创建限制
            "/api/v1/orders": RateLimitRule(
                max_requests=30,
                window_seconds=3600,
                scope="user"
            ),
        }

        # 启动清理任务
        asyncio.create_task(self._cleanup_loop())

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 跳过健康检查和 metrics
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)

        # 检查是否有匹配的规则
        rule = self._get_rule(request.url.path, request.method)
        if not rule:
            return await call_next(request)

        # 获取限制键
        key = self._get_limit_key(request, rule.scope)
        if not key:
            # 无法确定限制键（如未登录用户的 user scope），跳过限制
            return await call_next(request)

        # 检查速率限制
        now = time.time()
        bucket_key = (rule.scope, key, request.url.path)
        bucket = self.buckets[bucket_key]

        current_count = bucket.get_count(now, rule.window_seconds)

        if current_count >= rule.max_requests:
            # 超过限制
            retry_after = rule.window_seconds

            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": f"Rate limit exceeded. Max {rule.max_requests} requests per {rule.window_seconds} seconds.",
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(rule.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(now + retry_after)),
                }
            )

        # 记录请求
        bucket.add_request(now)

        # 处理请求
        response = await call_next(request)

        # 添加速率限制响应头
        remaining = rule.max_requests - (current_count + 1)
        response.headers["X-RateLimit-Limit"] = str(rule.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Reset"] = str(int(now + rule.window_seconds))

        return response

    def _get_rule(self, path: str, method: str) -> Optional[RateLimitRule]:
        """获取匹配的速率限制规则"""
        # 精确匹配
        if path in self.rules:
            return self.rules[path]

        # 前缀匹配
        for rule_path, rule in self.rules.items():
            if path.startswith(rule_path):
                return rule

        return None

    def _get_limit_key(self, request: Request, scope: str) -> Optional[str]:
        """获取限制键"""
        if scope == "ip":
            # 优先从 X-Forwarded-For 获取真实 IP
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                return forwarded.split(",")[0].strip()
            return request.client.host if request.client else "unknown"

        elif scope == "user":
            # 从请求状态获取用户 ID（由认证中间件设置）
            return getattr(request.state, "user_id", None)

        elif scope == "global":
            return "global"

        return None

    async def _cleanup_loop(self):
        """定期清理过期的桶"""
        while True:
            await asyncio.sleep(300)  # 每 5 分钟清理一次

            now = time.time()
            expired_keys = []

            for key, bucket in self.buckets.items():
                # 清理过期记录
                scope, limit_key, endpoint = key
                rule = self.rules.get(endpoint)
                if rule:
                    bucket.get_count(now, rule.window_seconds)

                # 如果桶为空，标记删除
                if not bucket.requests:
                    expired_keys.append(key)

            # 删除空桶
            for key in expired_keys:
                del self.buckets[key]


class RateLimitConfig:
    """速率限制配置（用于运行时动态调整）"""

    # 默认规则
    DEFAULT_RULES = {
        "auth_login": RateLimitRule(5, 60, "ip"),
        "sse_tickets": RateLimitRule(60, 3600, "user"),
        "task_creation": RateLimitRule(20, 3600, "user"),
        "order_creation": RateLimitRule(30, 3600, "user"),
    }

    @classmethod
    def get_rule(cls, name: str) -> Optional[RateLimitRule]:
        """获取规则"""
        return cls.DEFAULT_RULES.get(name)

    @classmethod
    def update_rule(cls, name: str, max_requests: int, window_seconds: int):
        """动态更新规则"""
        if name in cls.DEFAULT_RULES:
            cls.DEFAULT_RULES[name].max_requests = max_requests
            cls.DEFAULT_RULES[name].window_seconds = window_seconds


# 简化版：基于装饰器的速率限制（用于特定端点）
def rate_limit(max_requests: int, window_seconds: int, scope: str = "user"):
    """速率限制装饰器

    使用示例:
    @router.post("/api/v1/expensive-operation")
    @rate_limit(max_requests=5, window_seconds=3600, scope="user")
    async def expensive_operation():
        ...
    """
    def decorator(func):
        # 注册到全局规则（简化实现）
        # 实际使用时需要配合中间件
        func._rate_limit = RateLimitRule(max_requests, window_seconds, scope)
        return func
    return decorator
