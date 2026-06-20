"""SSE (Server-Sent Events) API for Real-time Task Progress"""

import uuid
from datetime import datetime
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from app.api.auth import get_current_user, UserInfo


router = APIRouter(prefix="/sse", tags=["sse"])

# In-memory ticket store (use Redis in production)
_ticket_store: Dict[str, tuple[str, datetime]] = {}


class TicketResponse(BaseModel):
    ticket: str
    expires_in: int = 60


@router.post("/tickets", response_model=TicketResponse)
async def create_ticket(
    current_user: UserInfo = Depends(get_current_user)
):
    """Create a one-time SSE ticket for subscribing to task events"""
    ticket = str(uuid.uuid4())
    expires = datetime.utcnow()
    _ticket_store[ticket] = (current_user.user_id, expires)
    
    return TicketResponse(ticket=ticket, expires_in=60)


async def validate_ticket(ticket: str) -> str:
    """Validate ticket and return user_id, delete after use"""
    if ticket not in _ticket_store:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired ticket"
        )
    
    user_id, expires = _ticket_store.pop(ticket)
    return user_id
