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

    For completed tasks, fetches the full result using cache-aside pattern.
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

    # For completed tasks, fetch full result (with cache-aside pattern)
    if task.state == TASK_STATE_COMPLETED:
        result = await task_service.get_task_result(task_id)
        if result and result.get("options"):
            response.options = result["options"]

    if task.state == TASK_STATE_FAILED and task.error_message:
        response.error = task.error_message

    return response

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
        # 发送初始 connected 事件
        yield f"event: connected\ndata: {json.dumps({'task_id': task_id})}\n\n"

        pubsub = redis.pubsub()
        await pubsub.psubscribe(f"task:{task_id}:*")

        # 已发送过的 event id 集合，用于 history 与 live 之间去重。
        # SSE 的 id 字段就是 Redis Stream 的 entry id（worker 写入时已带）。
        seen_ids: set[str] = set()

        # 心跳节流：每 30 秒一次，而不是每秒；空跑 1 秒只用于让 wait_for 醒来
        keepalive_interval_s = 30.0
        last_keepalive = 0.0

        try:
            # 1. 先回放历史（订阅已建立，订阅期间到达的消息会被 pubsub 缓冲）
            try:
                if last_event_id:
                    history = await task_service.get_event_history(
                        task_id,
                        last_event_id=f"({last_event_id}",
                    )
                else:
                    history = await task_service.get_event_history(task_id)
                for event in history:
                    eid = str(event.get("id", ""))
                    if eid:
                        seen_ids.add(eid)
                    line_id = f"id: {eid}\n" if eid else ""
                    yield (
                        f"{line_id}"
                        f"event: {event['type']}\n"
                        f"data: {json.dumps(event['data'])}\n\n"
                    )
            except Exception:
                # history 失败不致命，继续走 live；不再做"全量 fallback"以免重复发送
                pass

            # 2. live：consume pubsub 缓冲 + 后续实时事件
            terminal_seen = False
            import time as _time

            start_ts = _time.time()
            max_lifetime_s = 30 * 60  # 单连接最长 30 分钟

            while not terminal_seen:
                if _time.time() - start_ts > max_lifetime_s:
                    break

                try:
                    message = await asyncio.wait_for(
                        pubsub.get_message(ignore_subscribe_messages=True),
                        timeout=1.0,
                    )
                except asyncio.TimeoutError:
                    message = None

                now = _time.time()
                if message is None:
                    if now - last_keepalive >= keepalive_interval_s:
                        yield ": keepalive\n\n"
                        last_keepalive = now
                    continue

                if message.get("type") != "pmessage":
                    continue

                channel = message["channel"]
                data_str = message["data"]
                event_type = channel.rsplit(":", 1)[-1]

                try:
                    event_data = json.loads(data_str)
                    payload = event_data.get("data", {})
                    eid = str(event_data.get("id", ""))
                except json.JSONDecodeError:
                    yield f"event: {event_type}\ndata: {data_str}\n\n"
                    continue

                if eid and eid in seen_ids:
                    # 历史已发送过；丢弃避免重复
                    continue
                if eid:
                    seen_ids.add(eid)

                line_id = f"id: {eid}\n" if eid else ""
                yield (
                    f"{line_id}"
                    f"event: {event_type}\n"
                    f"data: {json.dumps(payload)}\n\n"
                )

                if event_type in ("done", "error"):
                    terminal_seen = True

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
