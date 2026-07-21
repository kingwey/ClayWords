"""SSE (Server-Sent Events) API for Real-time Task Progress"""

import uuid
from datetime import datetime
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel

from app.api.auth import get_current_user, UserInfo
from app.core.redis import RedisClient, get_redis


router = APIRouter(prefix="/sse", tags=["sse"])

# SSE ticket TTL (60 seconds)
TICKET_TTL = 60


class TicketResponse(BaseModel):
    ticket: str
    expires_in: int = TICKET_TTL


@router.post("/tickets", response_model=TicketResponse)
async def create_ticket(
    current_user: UserInfo = Depends(get_current_user),
    redis: RedisClient = Depends(get_redis),
):
    """Create a one-time SSE ticket for subscribing to task events.

    Stored in Redis with 60s TTL. Each ticket can be validated only once.
    """
    ticket = str(uuid.uuid4())
    key = f"sse:ticket:{ticket}"

    # Store user_id in Redis with TTL
    await redis.set(key, current_user.user_id, ex=TICKET_TTL)

    return TicketResponse(ticket=ticket, expires_in=TICKET_TTL)


async def validate_ticket(ticket: str, redis: Optional[RedisClient] = None) -> str:
    """Validate ticket and return user_id, delete after use.

    Multi-instance compatible: tickets are global via Redis.
    """
    if redis is None:
        redis = await get_redis()

    key = f"sse:ticket:{ticket}"
    user_id = await redis.get(key)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired ticket",
        )

    # One-time use: delete the ticket
    await redis.delete(key)

    return user_id
