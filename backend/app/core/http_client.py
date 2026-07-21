"""Global HTTP Client Manager

Provides a shared httpx.AsyncClient instance to avoid creating new connections
for every external API call. This prevents file descriptor exhaustion and
improves performance through connection pooling.

Usage:
    from app.core.http_client import get_http_client

    client = await get_http_client()
    response = await client.get("https://example.com")
"""

import httpx
from typing import Optional
import structlog

logger = structlog.get_logger()


class HTTPClientManager:
    """Singleton HTTP client manager with connection pooling"""

    _instance: Optional[httpx.AsyncClient] = None
    _lock = False  # Simple flag to prevent race conditions during initialization

    @classmethod
    async def get_client(cls) -> httpx.AsyncClient:
        """Get or create the shared HTTP client instance

        Returns:
            httpx.AsyncClient: Shared client with connection pooling enabled
        """
        if cls._instance is None or cls._instance.is_closed:
            # Simple lock mechanism (good enough for single-process scenarios)
            if not cls._lock:
                cls._lock = True
                try:
                    cls._instance = httpx.AsyncClient(
                        timeout=httpx.Timeout(
                            timeout=30.0,      # Total timeout
                            connect=10.0,      # Connection timeout
                            read=30.0,         # Read timeout
                            write=10.0,        # Write timeout
                        ),
                        limits=httpx.Limits(
                            max_connections=100,           # Total connections
                            max_keepalive_connections=20,  # Keep-alive pool size
                            keepalive_expiry=30.0,        # Keep-alive duration (seconds)
                        ),
                        follow_redirects=True,
                        http2=True,  # Enable HTTP/2 for better performance
                    )
                    logger.info(
                        "http_client_initialized",
                        max_connections=100,
                        max_keepalive=20,
                    )
                finally:
                    cls._lock = False

        return cls._instance

    @classmethod
    async def close(cls):
        """Close the HTTP client and release all connections

        Should be called during application shutdown.
        """
        if cls._instance and not cls._instance.is_closed:
            await cls._instance.aclose()
            cls._instance = None
            logger.info("http_client_closed")


# Convenience function for dependency injection
async def get_http_client() -> httpx.AsyncClient:
    """FastAPI dependency to get the shared HTTP client

    Usage:
        @router.get("/example")
        async def example(client: httpx.AsyncClient = Depends(get_http_client)):
            response = await client.get("https://api.example.com")
    """
    return await HTTPClientManager.get_client()


# Shutdown hook registration helper
async def shutdown_http_client():
    """Shutdown hook to be registered in main.py"""
    await HTTPClientManager.close()
