#!/usr/bin/env python3
"""
Phase Q2 端到端 Worker 测试

启动 worker 并提交任务，验证完整流程
"""

import asyncio
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.redis import redis_client
from app.services.tasks.task_service import (
    TaskService,
    STREAM_DESIGN_GEN,
    GROUP_DESIGN_WORKERS,
    TASK_STATE_COMPLETED,
)
from worker.consumer import DesignWorker


async def test_worker_e2e():
    """端到端测试：提交任务 → Worker 处理 → 验证完成"""
    print("=== Worker End-to-End Test ===\n")

    # Connect Redis
    await redis_client.connect()

    # Use test stream
    test_stream = "test:e2e:design.gen"
    test_group = "test:e2e:workers"

    # Cleanup any old data
    await redis_client.delete(test_stream)

    # Create a worker (in background)
    worker = DesignWorker(
        redis=redis_client,
        stream=test_stream,
        group=test_group,
        consumer_name="test-worker-1",
        block_ms=1000,
    )

    # Override task service for the test
    test_service = TaskService(redis_client)
    worker.task_service = test_service

    print("[1/4] Starting worker in background...")
    worker_task = asyncio.create_task(worker.run())
    await asyncio.sleep(0.5)

    print("[2/4] Submitting test task...")
    service = TaskService(redis_client)
    task = await service.create_task(
        payload={"test": True, "content": "test ceramic vase"},
        stream=test_stream,
    )
    print(f"     Task ID: {task.task_id}")

    print("[3/4] Waiting for worker to process...")
    # Wait up to 10 seconds for completion
    for i in range(20):
        await asyncio.sleep(0.5)
        result = await service.get_task(task.task_id)
        if result and result.state == TASK_STATE_COMPLETED:
            print(f"     [OK] Task completed in {(i+1)*0.5:.1f}s")
            print(f"     Result: {result.result_uri}")
            break
    else:
        print(f"     [FAIL] Task did not complete in 10s")
        print(f"     Final state: {result.state if result else 'None'}")
        worker.stop()
        await worker_task
        await redis_client.disconnect()
        return False

    print("[4/4] Stopping worker...")
    worker.stop()

    try:
        await asyncio.wait_for(worker_task, timeout=5.0)
    except asyncio.TimeoutError:
        worker_task.cancel()

    # Cleanup
    await redis_client.delete(test_stream)
    await redis_client.delete(f"task:{task.task_id}:state")
    await redis_client.delete(f"task:{task.task_id}:events")
    await redis_client.disconnect()

    print("\n[OK] End-to-end test passed!")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_worker_e2e())
    sys.exit(0 if success else 1)
