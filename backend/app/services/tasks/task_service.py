"""Task Service - Redis Streams + PostgreSQL persistence"""

import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import RedisClient, get_redis
from app.db.session import async_session_maker
from app.models.entities import Task as TaskModel


# Stream names
STREAM_DESIGN_GEN = "design.gen"
STREAM_DESIGN_GEN_DEAD = "design.gen.dead"
GROUP_DESIGN_WORKERS = "design.gen.workers"

# Task states
TASK_STATE_PENDING = "pending"
TASK_STATE_PROCESSING = "processing"
TASK_STATE_COMPLETED = "completed"
TASK_STATE_FAILED = "failed"


@dataclass
class TaskInfo:
    """Task information"""
    task_id: str
    state: str
    payload: dict
    progress: int = 0
    result_uri: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


class TaskService:
    """Manage tasks with Redis Streams + PostgreSQL persistence"""

    def __init__(self, redis: RedisClient):
        self.redis = redis

    async def create_task(
        self,
        payload: dict,
        task_id: Optional[str] = None,
        stream: str = STREAM_DESIGN_GEN,
    ) -> TaskInfo:
        """
        Create a new task:
        1. Persist to PostgreSQL (durability)
        2. Push to Redis Stream (queue)
        3. Cache state in Redis (fast read)
        """
        if task_id is None:
            task_id = str(uuid.uuid4())

        now = datetime.utcnow()

        # 1. Persist to PostgreSQL
        async with async_session_maker() as session:
            task = TaskModel(
                task_id=task_id,
                state=TASK_STATE_PENDING,
                payload=payload,
                progress=0,
                created_at=now,
                updated_at=now,
            )
            session.add(task)
            await session.commit()

        # 2. Push to Redis Stream (queue)
        await self.redis.xadd(
            stream,
            {
                "task_id": task_id,
                "payload": json.dumps(payload),
                "created_at": now.isoformat(),
            },
            maxlen=10000,  # Keep last 10000 entries
        )

        # 3. Cache state in Redis
        await self._cache_task_state(task_id, TASK_STATE_PENDING, payload=payload)

        return TaskInfo(
            task_id=task_id,
            state=TASK_STATE_PENDING,
            payload=payload,
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
        )

    async def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """
        Get task info, prefer Redis cache, fallback to PostgreSQL.
        """
        # 1. Try Redis first
        cached = await self.redis.get(f"task:{task_id}:state")
        if cached:
            data = json.loads(cached)
            return TaskInfo(**data)

        # 2. Fallback to PostgreSQL
        async with async_session_maker() as session:
            stmt = select(TaskModel).where(TaskModel.task_id == task_id)
            result = await session.execute(stmt)
            task = result.scalar_one_or_none()

            if task:
                info = TaskInfo(
                    task_id=task.task_id,
                    state=task.state,
                    payload=task.payload,
                    progress=task.progress,
                    result_uri=task.result_uri,
                    error_message=task.error_message,
                    created_at=task.created_at.isoformat() if task.created_at else None,
                    updated_at=task.updated_at.isoformat() if task.updated_at else None,
                )
                # Refresh cache
                await self._cache_task_state(
                    task_id,
                    task.state,
                    payload=task.payload,
                    progress=task.progress,
                    result_uri=task.result_uri,
                    error_message=task.error_message,
                )
                return info

        return None

    async def update_task_state(
        self,
        task_id: str,
        state: str,
        progress: Optional[int] = None,
        result_uri: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[TaskInfo]:
        """Update task state in both Redis and PostgreSQL"""
        now = datetime.utcnow()

        # 1. Update PostgreSQL
        async with async_session_maker() as session:
            stmt = select(TaskModel).where(TaskModel.task_id == task_id)
            result = await session.execute(stmt)
            task = result.scalar_one_or_none()

            if not task:
                return None

            task.state = state
            task.updated_at = now
            if progress is not None:
                task.progress = progress
            if result_uri is not None:
                task.result_uri = result_uri
            if error_message is not None:
                task.error_message = error_message

            await session.commit()

            payload = task.payload

        # 2. Update Redis cache
        await self._cache_task_state(
            task_id,
            state,
            payload=payload,
            progress=progress or 0,
            result_uri=result_uri,
            error_message=error_message,
        )

        return TaskInfo(
            task_id=task_id,
            state=state,
            payload=payload,
            progress=progress or 0,
            result_uri=result_uri,
            error_message=error_message,
            updated_at=now.isoformat(),
        )

    async def publish_progress(
        self,
        task_id: str,
        event_type: str,
        data: dict,
    ):
        """
        Publish progress event:
        1. Pub/Sub for real-time SSE
        2. Stream for replay support
        """
        event_data = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # 1. Publish to Pub/Sub channel
        await self.redis.publish(
            f"task:{task_id}:{event_type}",
            json.dumps(event_data),
        )

        # 2. Add to event stream for replay
        await self.redis.xadd(
            f"task:{task_id}:events",
            {
                "type": event_type,
                "data": json.dumps(data),
                "timestamp": event_data["timestamp"],
            },
            maxlen=1000,  # Keep last 1000 events
        )

        # 3. Set TTL on the event stream (1 hour)
        await self.redis.expire(f"task:{task_id}:events", 3600)

    async def get_event_history(
        self,
        task_id: str,
        last_event_id: str = "-",
    ) -> List[Dict[str, Any]]:
        """Get event history for replay (used in SSE Last-Event-ID)"""
        events = await self.redis.xrange(
            f"task:{task_id}:events",
            min=last_event_id,
            max="+",
        )

        result = []
        for event_id, fields in events:
            result.append({
                "id": event_id,
                "type": fields.get("type"),
                "data": json.loads(fields.get("data", "{}")),
                "timestamp": fields.get("timestamp"),
            })

        return result

    async def _cache_task_state(
        self,
        task_id: str,
        state: str,
        payload: Optional[dict] = None,
        progress: int = 0,
        result_uri: Optional[str] = None,
        error_message: Optional[str] = None,
        ttl: int = 3600,
    ):
        """Cache task state in Redis"""
        info = {
            "task_id": task_id,
            "state": state,
            "payload": payload or {},
            "progress": progress,
            "result_uri": result_uri,
            "error_message": error_message,
            "updated_at": datetime.utcnow().isoformat(),
        }
        await self.redis.set(
            f"task:{task_id}:state",
            json.dumps(info),
            ex=ttl,
        )


# Singleton accessor
_task_service: Optional[TaskService] = None


async def get_task_service() -> TaskService:
    """Get task service instance"""
    global _task_service
    if _task_service is None:
        redis = await get_redis()
        _task_service = TaskService(redis)
    return _task_service
