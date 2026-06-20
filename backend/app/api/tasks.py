"""Tasks API for Design Generation Tasks"""

import uuid
import json
import asyncio
from datetime import datetime
from typing import Dict, Optional, List
from fastapi import APIRouter, HTTPException, Depends, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.auth import get_current_user, UserInfo
from app.api.sse import validate_ticket
from app.db.session import get_session
from app.models.entities import Session as SessionModel, Design as DesignModel, DesignVersion as DesignVersionModel


router = APIRouter(prefix="/tasks", tags=["tasks"])

# In-memory task store (use Redis in production)
_task_status: Dict[str, str] = {}
_task_options: Dict[str, List[str]] = {}
_task_events: Dict[str, asyncio.Queue] = {}


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # pending, processing, completed, failed
    options: Optional[List[str]] = None
    error: Optional[str] = None


@router.get("/{task_id}/events")
async def stream_task_events(
    task_id: str,
    ticket: str = Query(...),
    current_user: UserInfo = Depends(get_current_user)
):
    """Stream SSE events for a task using ticket authentication"""
    # Validate ticket
    ticket_user_id = await validate_ticket(ticket)
    if ticket_user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ticket does not match current user"
        )

    # Create event queue for this task if not exists
    if task_id not in _task_events:
        _task_events[task_id] = asyncio.Queue()

    async def event_generator():
        queue = _task_events[task_id]
        timeout_count = 0
        max_timeouts = 30  # 30 seconds timeout
        
        # Send initial connection event
        yield f"event: connected\ndata: {json.dumps({'task_id': task_id})}\n\n"
        
        while timeout_count < max_timeouts:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=1.0)
                yield f"event: {event['type']}\ndata: {json.dumps(event['data'])}\n\n"
                
                if event['type'] in ('done', 'error'):
                    break
            except asyncio.TimeoutError:
                timeout_count += 1
                # Send keepalive
                yield f": keepalive\n\n"
        
        yield f"event: done\ndata: {json.dumps({'status': 'completed'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: UserInfo = Depends(get_current_user)
):
    """Get final task status (fallback for disconnected clients)"""
    status_str = _task_status.get(task_id, "pending")
    
    result = TaskStatusResponse(
        task_id=task_id,
        status=status_str
    )
    
    if status_str == "completed":
        result.options = _task_options.get(task_id)
    elif status_str == "failed":
        result.error = "Task processing failed"
    
    return result


# Utility functions for publishing task events
async def publish_task_event(task_id: str, event_type: str, data: dict):
    """Publish an event to a task's queue"""
    if task_id in _task_events:
        event = {"type": event_type, "data": data, "timestamp": datetime.utcnow().isoformat()}
        await _task_events[task_id].put(event)


async def set_task_status(task_id: str, status: str, options: Optional[List[str]] = None, error: Optional[str] = None):
    """Set task status"""
    _task_status[task_id] = status
    if options:
        _task_options[task_id] = options
    if error:
        await publish_task_event(task_id, "error", {"error": error})
