"""ClayWords - FastAPI Application Entry Point"""

import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, health, sessions, sse, tasks, options, orders, demo
from app.core.config import settings
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
    yield
    logger.info("application_shutdown")


app = FastAPI(
    title="ClayWords API",
    description="AI-powered ceramic customization platform",
    version=settings.VERSION,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Health check
app.include_router(health.router, tags=["health"])

# API routes
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["sessions"])
app.include_router(sse.router, prefix="/api/v1", tags=["sse"])
app.include_router(tasks.router, prefix="/api/v1", tags=["tasks"])
app.include_router(options.router, prefix="/api/v1", tags=["options"])
app.include_router(orders.router, prefix="/api/v1", tags=["orders"])
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
