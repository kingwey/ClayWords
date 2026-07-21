#!/usr/bin/env python3
"""
Phase Q2 验证脚本

测试 Redis Streams + 任务队列 + SSE Pub/Sub 系统
"""

import asyncio
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.redis import redis_client
from app.services.tasks.task_service import (
    TaskService,
    STREAM_DESIGN_GEN,
    GROUP_DESIGN_WORKERS,
    TASK_STATE_PENDING,
    TASK_STATE_PROCESSING,
    TASK_STATE_COMPLETED,
)


async def test_redis_connection():
    """测试 Redis 连接"""
    print("Testing Redis connection...", end=" ")
    try:
        await redis_client.connect()
        await redis_client.set("test:ping", "pong", ex=10)
        value = await redis_client.get("test:ping")
        if value == "pong":
            print("[OK] Redis connected")
            await redis_client.delete("test:ping")
            return True
        else:
            print(f"[FAIL] Unexpected value: {value}")
            return False
    except Exception as e:
        print(f"[FAIL] {e}")
        return False


async def test_streams_basic():
    """测试 Redis Streams 基础操作"""
    print("\nTesting Redis Streams...", end=" ")
    try:
        # Add to stream
        msg_id = await redis_client.xadd(
            "test:stream",
            {"key1": "value1", "key2": "value2"}
        )
        if not msg_id:
            print("[FAIL] xadd returned no id")
            return False

        # Read range
        entries = await redis_client.xrange("test:stream")
        if len(entries) >= 1:
            print(f"[OK] Streams working ({len(entries)} entries)")
        else:
            print("[FAIL] xrange returned no entries")
            return False

        # Cleanup
        await redis_client.delete("test:stream")
        return True
    except Exception as e:
        print(f"[FAIL] {e}")
        return False


async def test_consumer_group():
    """测试 Consumer Group"""
    print("\nTesting Consumer Group...", end=" ")
    try:
        stream_name = f"test:cg:{uuid.uuid4().hex[:8]}"
        group_name = "test_group"
        consumer_name = "test_consumer"

        # Create group
        await redis_client.xgroup_create(
            stream_name, group_name, id="0", mkstream=True
        )

        # Add a message
        msg_id = await redis_client.xadd(
            stream_name,
            {"data": "test_message"}
        )

        # Read as consumer
        messages = await redis_client.xreadgroup(
            group_name,
            consumer_name,
            {stream_name: ">"},
            count=1,
            block=1000,
        )

        if messages and len(messages) > 0:
            stream, entries = messages[0]
            if entries:
                # ACK the message
                await redis_client.xack(stream_name, group_name, entries[0][0])
                print("[OK] Consumer Group working")

                # Cleanup
                await redis_client.delete(stream_name)
                return True

        print("[FAIL] No messages received")
        return False

    except Exception as e:
        print(f"[FAIL] {e}")
        return False


async def test_task_service_create():
    """测试任务创建"""
    print("\nTesting TaskService.create_task...", end=" ")
    try:
        service = TaskService(redis_client)

        # Use temporary stream for testing
        test_stream = f"test:design.gen:{uuid.uuid4().hex[:8]}"

        task = await service.create_task(
            payload={"test": "payload", "user_id": "test_user"},
            stream=test_stream,
        )

        if task and task.task_id:
            # Verify task was created
            retrieved = await service.get_task(task.task_id)
            if retrieved and retrieved.state == TASK_STATE_PENDING:
                print(f"[OK] Task created: {task.task_id[:8]}...")

                # Cleanup
                await redis_client.delete(test_stream)
                await redis_client.delete(f"task:{task.task_id}:state")
                return True

        print("[FAIL] Task creation incomplete")
        return False

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[FAIL] {e}")
        return False


async def test_task_state_transitions():
    """测试任务状态转换"""
    print("\nTesting task state transitions...", end=" ")
    try:
        service = TaskService(redis_client)

        test_stream = f"test:state:{uuid.uuid4().hex[:8]}"
        task = await service.create_task(
            payload={"test": True},
            stream=test_stream,
        )

        # Pending → Processing
        await service.update_task_state(task.task_id, TASK_STATE_PROCESSING, progress=50)
        retrieved = await service.get_task(task.task_id)
        if retrieved.state != TASK_STATE_PROCESSING:
            print(f"[FAIL] State not updated to processing")
            return False

        # Processing → Completed
        await service.update_task_state(
            task.task_id,
            TASK_STATE_COMPLETED,
            progress=100,
            result_uri="test://result",
        )
        retrieved = await service.get_task(task.task_id)
        if retrieved.state != TASK_STATE_COMPLETED or retrieved.progress != 100:
            print(f"[FAIL] Not completed properly")
            return False

        print("[OK] State transitions working")

        # Cleanup
        await redis_client.delete(test_stream)
        await redis_client.delete(f"task:{task.task_id}:state")
        return True

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[FAIL] {e}")
        return False


async def test_pubsub_progress():
    """测试 Pub/Sub 进度发布"""
    print("\nTesting Pub/Sub progress...", end=" ")
    try:
        service = TaskService(redis_client)
        task_id = str(uuid.uuid4())

        # Subscribe in background
        received_events = []

        async def subscriber():
            pubsub = redis_client.pubsub()
            await pubsub.psubscribe(f"task:{task_id}:*")

            # Listen for a few seconds
            try:
                end_time = asyncio.get_event_loop().time() + 3
                while asyncio.get_event_loop().time() < end_time:
                    message = await asyncio.wait_for(
                        pubsub.get_message(ignore_subscribe_messages=True),
                        timeout=0.5,
                    )
                    if message and message.get("type") == "pmessage":
                        received_events.append(message)
                        if len(received_events) >= 2:
                            break
            except asyncio.TimeoutError:
                pass
            finally:
                await pubsub.punsubscribe(f"task:{task_id}:*")
                await pubsub.close()

        # Start subscriber
        sub_task = asyncio.create_task(subscriber())
        await asyncio.sleep(0.3)  # Let subscriber initialize

        # Publish events
        await service.publish_progress(task_id, "progress", {"value": 25})
        await service.publish_progress(task_id, "progress", {"value": 50})

        # Wait for subscriber
        await sub_task

        if len(received_events) >= 2:
            print(f"[OK] Pub/Sub working ({len(received_events)} events)")

            # Cleanup
            await redis_client.delete(f"task:{task_id}:events")
            return True
        else:
            print(f"[FAIL] Only {len(received_events)} events received")
            return False

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[FAIL] {e}")
        return False


async def test_event_history_replay():
    """测试事件历史回放（Last-Event-ID 支持）"""
    print("\nTesting event history replay...", end=" ")
    try:
        service = TaskService(redis_client)
        task_id = str(uuid.uuid4())

        # Publish multiple events
        await service.publish_progress(task_id, "start", {"msg": "starting"})
        await service.publish_progress(task_id, "progress", {"value": 33})
        await service.publish_progress(task_id, "progress", {"value": 66})
        await service.publish_progress(task_id, "done", {"msg": "complete"})

        # Get full history
        history = await service.get_event_history(task_id)

        if len(history) == 4:
            print(f"[OK] Event history working ({len(history)} events)")

            # Cleanup
            await redis_client.delete(f"task:{task_id}:events")
            return True
        else:
            print(f"[FAIL] Expected 4 events, got {len(history)}")
            return False

    except Exception as e:
        print(f"[FAIL] {e}")
        return False


async def test_sse_ticket_redis():
    """测试 SSE 票据存储到 Redis"""
    print("\nTesting SSE tickets in Redis...", end=" ")
    try:
        ticket = str(uuid.uuid4())
        user_id = "test_user_123"

        # Set ticket
        await redis_client.set(f"sse:ticket:{ticket}", user_id, ex=60)

        # Get ticket
        retrieved = await redis_client.get(f"sse:ticket:{ticket}")

        if retrieved == user_id:
            # Delete (one-time use)
            await redis_client.delete(f"sse:ticket:{ticket}")

            # Verify deletion
            after_delete = await redis_client.get(f"sse:ticket:{ticket}")
            if after_delete is None:
                print("[OK] SSE tickets working")
                return True

        print("[FAIL] Ticket validation issue")
        return False

    except Exception as e:
        print(f"[FAIL] {e}")
        return False


async def main():
    print("=== Phase Q2 Verification ===\n")

    results = []

    # Run all tests
    results.append(await test_redis_connection())
    results.append(await test_streams_basic())
    results.append(await test_consumer_group())
    results.append(await test_task_service_create())
    results.append(await test_task_state_transitions())
    results.append(await test_pubsub_progress())
    results.append(await test_event_history_replay())
    results.append(await test_sse_ticket_redis())

    # Cleanup
    await redis_client.disconnect()

    # Summary
    print("\n=== Summary ===")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n[OK] All tests passed! Phase Q2 is complete.")
        return 0
    else:
        print(f"\n[FAIL] {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
