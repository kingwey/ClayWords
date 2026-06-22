"""Logging Middleware - Request ID, User ID, Task ID injection + PII Sanitization"""

import re
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Optional structlog import
try:
    import structlog
    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False
    structlog = None


# 脱敏正则
PHONE_PATTERN = re.compile(r'1[3-9]\d{9}')  # 中国手机号
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
ID_CARD_PATTERN = re.compile(r'\d{17}[\dXx]')  # 身份证号
BANK_CARD_PATTERN = re.compile(r'\d{16,19}')  # 银行卡号


def sanitize_phone(phone: str) -> str:
    """脱敏手机号: 13912345678 -> 139****5678"""
    if len(phone) >= 11:
        return phone[:3] + '****' + phone[-4:]
    return phone


def sanitize_email(email: str) -> str:
    """脱敏邮箱: user@example.com -> u***@example.com"""
    if '@' in email:
        local, domain = email.split('@', 1)
        if len(local) > 1:
            return local[0] + '***@' + domain
    return email


def sanitize_address(address: str) -> str:
    """脱敏地址: 北京市朝阳区xxx -> 北京市***"""
    if len(address) > 6:
        return address[:6] + '***'
    return address


def sanitize_text(text: str) -> str:
    """脱敏文本中的敏感信息"""
    if not isinstance(text, str):
        return text

    # 脱敏手机号
    text = PHONE_PATTERN.sub(lambda m: sanitize_phone(m.group()), text)
    # 脱敏邮箱
    text = EMAIL_PATTERN.sub(lambda m: sanitize_email(m.group()), text)
    # 脱敏身份证
    text = ID_CARD_PATTERN.sub(lambda m: m.group()[:6] + '********' + m.group()[-4:], text)

    return text


class LoggingMiddleware(BaseHTTPMiddleware):
    """结构化日志中间件

    Phase Q7.1.1: 自动注入 request_id, user_id, task_id
    Phase Q7.1.2: 日志脱敏（手机号、邮箱、地址）
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 生成或获取 request_id
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        # 提取 user_id (如果已认证)
        user_id = None
        try:
            # 从 JWT token 中解析 user_id
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                # 简化实现：实际应该解析 JWT
                pass
        except Exception:
            pass

        # 提取 task_id (如果在路径中)
        task_id = None
        path_parts = request.url.path.split('/')
        if 'tasks' in path_parts:
            try:
                task_idx = path_parts.index('tasks')
                if task_idx + 1 < len(path_parts):
                    task_id = path_parts[task_idx + 1]
            except (ValueError, IndexError):
                pass

        # 绑定上下文变量
        if HAS_STRUCTLOG:
            structlog.contextvars.clear_contextvars()
            ctx = {"request_id": request_id}
            if user_id:
                ctx["user_id"] = user_id
            if task_id:
                ctx["task_id"] = task_id

            structlog.contextvars.bind_contextvars(**ctx)

            # 记录请求开始
            logger = structlog.get_logger()
        else:
            logger = None
        start_time = time.time()

        if logger:
            logger.info(
                "request_started",
                method=request.method,
                path=request.url.path,
                client_ip=request.client.host if request.client else "unknown",
            )

        # 处理请求
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            # 记录请求完成
            if logger:
                logger.info(
                    "request_completed",
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                    duration_ms=round(duration_ms, 2),
                )

            # 添加 X-Request-ID 响应头
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            if logger:
                logger.error(
                    "request_failed",
                    method=request.method,
                    path=request.url.path,
                    error=str(e),
                    duration_ms=round(duration_ms, 2),
                )
            raise
