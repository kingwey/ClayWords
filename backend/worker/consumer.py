"""Design Generation Worker - Redis Streams Consumer"""

import asyncio
import json
import logging
import signal
import socket
import uuid
from datetime import datetime
from typing import Optional, Callable, Awaitable

from app.core.redis import RedisClient, redis_client
from app.services.tasks.task_service import (
    TaskService,
    STREAM_DESIGN_GEN,
    STREAM_DESIGN_GEN_DEAD,
    GROUP_DESIGN_WORKERS,
    TASK_STATE_PROCESSING,
    TASK_STATE_COMPLETED,
    TASK_STATE_FAILED,
)


logger = logging.getLogger(__name__)


# Default task handler type
TaskHandler = Callable[[str, dict, "DesignWorker"], Awaitable[dict]]


class DesignWorker:
    """Redis Streams consumer for design generation tasks"""

    def __init__(
        self,
        redis: RedisClient,
        stream: str = STREAM_DESIGN_GEN,
        group: str = GROUP_DESIGN_WORKERS,
        consumer_name: Optional[str] = None,
        max_retries: int = 3,
        block_ms: int = 5000,
        idle_threshold_ms: int = 300000,  # 5 minutes
    ):
        self.redis = redis
        self.stream = stream
        self.group = group
        self.consumer_name = consumer_name or f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"
        self.max_retries = max_retries
        self.block_ms = block_ms
        self.idle_threshold_ms = idle_threshold_ms
        self.task_service = TaskService(redis)
        self.handler: Optional[TaskHandler] = None
        self._running = False
        self._retry_counts: dict = {}

    def set_handler(self, handler: TaskHandler):
        """Set the task handler function"""
        self.handler = handler

    async def setup(self):
        """Initialize consumer group"""
        await self.redis.xgroup_create(
            self.stream,
            self.group,
            id="0",
            mkstream=True,
        )
        logger.info(
            f"Worker initialized: stream={self.stream}, "
            f"group={self.group}, consumer={self.consumer_name}"
        )

    async def claim_pending(self):
        """Claim long-pending messages from other consumers (recovery)"""
        try:
            pending = await self.redis.xpending(
                self.stream,
                self.group,
                count=100,
            )

            stale_ids = []
            for entry in pending:
                # entry: {message_id, consumer, time_since_delivered, times_delivered}
                idle_time = entry.get("time_since_delivered", 0)
                if idle_time > self.idle_threshold_ms:
                    stale_ids.append(entry["message_id"])

            if stale_ids:
                logger.info(f"Claiming {len(stale_ids)} stale messages")
                claimed = await self.redis.xclaim(
                    self.stream,
                    self.group,
                    self.consumer_name,
                    self.idle_threshold_ms,
                    stale_ids,
                )
                return claimed
        except Exception as e:
            logger.error(f"Failed to claim pending: {e}")

        return []

    async def process_message(self, message_id: str, fields: dict):
        """Process a single message"""
        task_id = fields.get("task_id")
        if not task_id:
            logger.error(f"Message {message_id} has no task_id")
            await self.redis.xack(self.stream, self.group, message_id)
            return

        try:
            # Parse payload
            payload = json.loads(fields.get("payload", "{}"))

            # Update task state to processing
            await self.task_service.update_task_state(
                task_id,
                TASK_STATE_PROCESSING,
                progress=0,
            )

            # Publish start event
            await self.task_service.publish_progress(
                task_id,
                "start",
                {"message": "Task processing started"},
            )

            # Call handler
            if self.handler:
                result = await self.handler(task_id, payload, self)
            else:
                # Default handler (mock)
                result = await self._default_handler(task_id, payload)

            # Update task state to completed
            await self.task_service.update_task_state(
                task_id,
                TASK_STATE_COMPLETED,
                progress=100,
                result_uri=result.get("result_uri"),
            )

            # Publish done event
            await self.task_service.publish_progress(
                task_id,
                "done",
                result,
            )

            # ACK the message
            await self.redis.xack(self.stream, self.group, message_id)

            # Reset retry count
            self._retry_counts.pop(message_id, None)

            logger.info(f"Task {task_id} completed successfully")

        except Exception as e:
            logger.exception(f"Task {task_id} failed: {e}")
            await self._handle_failure(message_id, task_id, fields, str(e))

    async def _default_handler(self, task_id: str, payload: dict) -> dict:
        """Default task handler (mock implementation)"""
        # Simulate progress
        for progress in [25, 50, 75]:
            await asyncio.sleep(0.5)
            await self.task_service.publish_progress(
                task_id,
                "progress",
                {"progress": progress, "message": f"Processing... {progress}%"},
            )

        return {
            "result_uri": f"mock://result/{task_id}",
            "options": [
                {"name": "Option 1", "score": 0.95},
                {"name": "Option 2", "score": 0.88},
                {"name": "Option 3", "score": 0.82},
            ],
        }

    async def _handle_failure(
        self,
        message_id: str,
        task_id: str,
        fields: dict,
        error_message: str,
    ):
        """Handle task failure with retry logic"""
        retry_count = self._retry_counts.get(message_id, 0) + 1
        self._retry_counts[message_id] = retry_count

        if retry_count >= self.max_retries:
            # Move to dead-letter queue
            await self.redis.xadd(
                STREAM_DESIGN_GEN_DEAD,
                {
                    "task_id": task_id,
                    "original_id": message_id,
                    "payload": fields.get("payload", "{}"),
                    "error": error_message,
                    "retry_count": retry_count,
                    "failed_at": datetime.utcnow().isoformat(),
                },
            )

            # Update task state to failed
            await self.task_service.update_task_state(
                task_id,
                TASK_STATE_FAILED,
                error_message=error_message,
            )

            # Publish error event
            await self.task_service.publish_progress(
                task_id,
                "error",
                {"error": error_message, "retry_count": retry_count},
            )

            # ACK to remove from pending
            await self.redis.xack(self.stream, self.group, message_id)

            logger.error(
                f"Task {task_id} moved to dead-letter after {retry_count} retries"
            )
        else:
            # Don't ACK - will be retried
            logger.warning(
                f"Task {task_id} failed (attempt {retry_count}/{self.max_retries}), will retry"
            )

    async def run(self):
        """Main consumer loop"""
        self._running = True
        await self.setup()

        # First, claim any pending stale messages
        stale_messages = await self.claim_pending()
        for msg_id, fields in stale_messages:
            await self.process_message(msg_id, fields)

        logger.info(f"Worker {self.consumer_name} starting consumer loop")

        while self._running:
            try:
                # Read from stream as consumer group
                messages = await self.redis.xreadgroup(
                    self.group,
                    self.consumer_name,
                    {self.stream: ">"},  # ">" = only new messages
                    count=1,
                    block=self.block_ms,
                )

                if not messages:
                    continue

                for stream_name, entries in messages:
                    for message_id, fields in entries:
                        await self.process_message(message_id, fields)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Worker error: {e}")
                await asyncio.sleep(1)  # Brief pause before retry

        logger.info(f"Worker {self.consumer_name} stopped")

    def stop(self):
        """Signal worker to stop"""
        self._running = False


async def run_worker(handler: Optional[TaskHandler] = None):
    """Run a worker instance"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Initialize Redis
    await redis_client.connect()

    worker = DesignWorker(redis_client)
    if handler:
        worker.set_handler(handler)

    # Setup graceful shutdown
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, worker.stop)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass

    try:
        await worker.run()
    finally:
        await redis_client.disconnect()


if __name__ == "__main__":
    asyncio.run(run_worker())
