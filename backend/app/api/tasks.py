"""Tasks API - Redis Streams + Pub/Sub powered"""

import json
import asyncio
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, status, Query, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.auth import get_current_user, UserInfo
from app.api.sse import validate_ticket
from app.core.redis import RedisClient, get_redis
from app.services.tasks.task_service import (
    TaskService,
    get_task_service,
    TASK_STATE_COMPLETED,
    TASK_STATE_FAILED,
)


router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # pending, processing, completed, failed
    progress: int = 0
    options: Optional[List[dict]] = None
    result_uri: Optional[str] = None
    error: Optional[str] = None


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: UserInfo = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service),
):
    """Get task status (used as fallback for disconnected clients).

    Reads from Redis cache first, falls back to PostgreSQL.
    """
    task = await task_service.get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    response = TaskStatusResponse(
        task_id=task.task_id,
        status=task.state,
        progress=task.progress,
        result_uri=task.result_uri,
    )

    if task.state == TASK_STATE_FAILED and task.error_message:
        response.error = task.error_message

    return response


@router.get("/{task_id}/events")
async def stream_task_events(
    task_id: str,
    ticket: str = Query(...),
    last_event_id: Optional[str] = Header(None, alias="Last-Event-ID"),
    current_user: UserInfo = Depends(get_current_user),
    redis: RedisClient = Depends(get_redis),
    task_service: TaskService = Depends(get_task_service),
):
    """Stream SSE events for a task using Redis Pub/Sub.

    Features:
    - Ticket-based authentication (one-time use)
    - Last-Event-ID support for reconnection (replays missed events from Redis Stream)
    - Real-time updates via Redis Pub/Sub
    """
    # Validate ticket
    ticket_user_id = await validate_ticket(ticket, redis)
    if ticket_user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ticket does not match current user",
        )

    async def event_generator():
        # Send initial connection event
        yield f"event: connected\ndata: {json.dumps({'task_id': task_id})}\n\n"

        # 1. Replay history if Last-Event-ID provided
        if last_event_id:
            try:
                # Range start should be after last_event_id
                history = await task_service.get_event_history(
                    task_id,
                    last_event_id=f"({last_event_id}",  # exclusive range start
                )
                for event in history:
                    yield (
                        f"id: {event['id']}\n"
                        f"event: {event['type']}\n"
                        f"data: {json.dumps(event['data'])}\n\n"
                    )
            except Exception:
                # Fallback: send all history
                history = await task_service.get_event_history(task_id)
                for event in history:
                    yield (
                        f"id: {event['id']}\n"
                        f"event: {event['type']}\n"
                        f"data: {json.dumps(event['data'])}\n\n"
                    )

        # 2. Subscribe to live events via Pub/Sub
        pubsub = redis.pubsub()
        await pubsub.psubscribe(f"task:{task_id}:*")

        try:
            timeout_count = 0
            max_timeouts = 600  # 10 minutes

            while timeout_count < max_timeouts:
                try:
                    message = await asyncio.wait_for(
                        pubsub.get_message(ignore_subscribe_messages=True),
                        timeout=1.0,
                    )

                    if message is None:
                        timeout_count += 1
                        # Send keepalive every second
                        yield ": keepalive\n\n"
                        continue

                    if message["type"] == "pmessage":
                        timeout_count = 0
                        channel = message["channel"]
                        data_str = message["data"]

                        # Parse channel: task:<id>:<event_type>
                        event_type = channel.rsplit(":", 1)[-1]

                        try:
                            event_data = json.loads(data_str)
                            payload = event_data.get("data", {})

                            yield (
                                f"event: {event_type}\n"
                                f"data: {json.dumps(payload)}\n\n"
                            )

                            # Stop on terminal events
                            if event_type in ("done", "error"):
                                break
                        except json.JSONDecodeError:
                            yield f"event: {event_type}\ndata: {data_str}\n\n"

                except asyncio.TimeoutError:
                    timeout_count += 1
                    yield ": keepalive\n\n"

        finally:
            await pubsub.punsubscribe(f"task:{task_id}:*")
            await pubsub.close()

        yield f"event: close\ndata: {json.dumps({'reason': 'stream_closed'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============== Compatibility helpers ==============

async def publish_task_event(task_id: str, event_type: str, data: dict):
    """Publish an event (compatibility wrapper).

    Replaces the legacy in-memory queue mechanism.
    """
    task_service = await get_task_service()
    await task_service.publish_progress(task_id, event_type, data)


async def set_task_status(
    task_id: str,
    status: str,
    options: Optional[List] = None,
    error: Optional[str] = None,
):
    """Set task status (compatibility wrapper)."""
    task_service = await get_task_service()
    result_uri = None
    if options:
        result_uri = json.dumps(options)
    await task_service.update_task_state(
        task_id,
        status,
        result_uri=result_uri,
        error_message=error,
    )
    if error:
        await task_service.publish_progress(task_id, "error", {"error": error})
