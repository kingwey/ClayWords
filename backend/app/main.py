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
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
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
