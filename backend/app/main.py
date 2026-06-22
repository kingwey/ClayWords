"""ClayWords - FastAPI Application Entry Point"""

import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, health, sessions, sse, tasks, options, orders, demo, uploads, studio_onboarding, studio_orders, payments, logistics, metrics, alerts
from app.core.config import settings
from app.core.redis import redis_client
from app.core.storage import minio_client
from app.core.logging_middleware import LoggingMiddleware
from app.core.metrics import PrometheusMiddleware
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
    await redis_client.disconnect()
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

# Phase Q7: Observability Middleware
app.add_middleware(PrometheusMiddleware)
app.add_middleware(LoggingMiddleware)


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
app.include_router(demo.router, prefix="/api/v1", tags=["demo"])
