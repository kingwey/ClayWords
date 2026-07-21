"""ClayWords - FastAPI Application Entry Point"""

import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auth, health, sessions, sse, tasks, options, orders, demo, uploads, studio_onboarding, studio_orders, payments, logistics, metrics, alerts, hunyuan3d, admin
from app.core.config import settings
from app.core.redis import redis_client
from app.core.storage import minio_client
from app.core.http_client import shutdown_http_client
from app.core.logging_middleware import LoggingMiddleware
from app.core.metrics import PrometheusMiddleware
from app.core.rate_limit import RateLimitMiddleware
from app.db.session import init_db


structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("application_startup", version=settings.VERSION)
    await init_db()
    logger.info("database_initialized")
    await redis_client.connect()
    logger.info("redis_connected", url=settings.REDIS_URL)
    try:
        minio_client.connect()
        logger.info("minio_connected", endpoint=settings.MINIO_ENDPOINT)
    except Exception as e:
        logger.warning("minio_connection_failed", error=str(e))
    yield
    await shutdown_http_client()
    logger.info("http_client_shutdown")
    await redis_client.disconnect()
    logger.info("application_shutdown")


app = FastAPI(
    title="ClayWords API",
    description="AI-powered ceramic customization platform",
    version=settings.VERSION,
    lifespan=lifespan,
)

# CORS (P0: 显式列举方法和 headers，配合 allow_credentials=True)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Idempotency-Key",
        "Last-Event-ID",
        "X-Requested-With",
    ],
    expose_headers=[
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "Retry-After",
    ],
)

# Phase Q7: Observability Middleware
# Starlette 中间件是 LIFO（后 add 在外层）。
# 期望 Prometheus 度量包含 LoggingMiddleware 的耗时 → 让 Prom 在最外层（后 add）。
# 速率限制夹在两者之间：Prom 仍能记录 429，但 429 不进业务日志噪音。
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(PrometheusMiddleware)


# 全局异常兜底：未被业务捕获的异常落到这里，统一结构化日志 + 不泄露 traceback
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    trace_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    logger.exception(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        trace_id=trace_id,
        error_type=type(exc).__name__,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "internal_server_error",
            "trace_id": trace_id,
        },
    )


# Health check
app.include_router(health.router, tags=["health"])

# Metrics endpoint (Phase Q7)
app.include_router(metrics.router, tags=["metrics"])
app.include_router(alerts.router, prefix="/api/v1", tags=["alerts"])

# API routes
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["sessions"])
app.include_router(sse.router, prefix="/api/v1", tags=["sse"])
app.include_router(tasks.router, prefix="/api/v1", tags=["tasks"])
app.include_router(options.router, prefix="/api/v1", tags=["options"])
app.include_router(orders.router, prefix="/api/v1", tags=["orders"])
app.include_router(uploads.router, prefix="/api/v1", tags=["uploads"])
app.include_router(studio_onboarding.router, prefix="/api/v1", tags=["studio-onboarding"])
app.include_router(studio_orders.router, prefix="/api/v1", tags=["studio-orders"])
app.include_router(payments.router, prefix="/api/v1", tags=["payments"])
app.include_router(logistics.router, prefix="/api/v1", tags=["logistics"])
app.include_router(hunyuan3d.router, prefix="/api/v1", tags=["hunyuan3d"])
app.include_router(admin.router, prefix="/api/v1", tags=["admin"])
app.include_router(demo.router, prefix="/api/v1", tags=["demo"])


# 同源托管前端构建产物（SPA）。设置 STATIC_DIR 后生效；
# 未匹配到静态文件的路径回退到 index.html，交给前端路由处理。
if settings.STATIC_DIR:
    import os

    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    _static_dir = settings.STATIC_DIR
    _index_file = os.path.join(_static_dir, "index.html")

    if os.path.isdir(_static_dir):
        _assets_dir = os.path.join(_static_dir, "assets")
        if os.path.isdir(_assets_dir):
            app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str):
            candidate = os.path.join(_static_dir, full_path)
            if full_path and os.path.isfile(candidate):
                return FileResponse(candidate)
            return FileResponse(_index_file)
