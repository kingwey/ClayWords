"""task_service 单元测试

覆盖目标：services/tasks/task_service.py 之前覆盖率 39%。
TaskService 同时操作 PG（双写持久化）和 Redis（缓存 + 队列 + Pub/Sub），
要在不依赖外部 Redis 的前提下覆盖关键路径，需要：
  - SQLite in-memory 替换全局 async_session_maker（monkeypatch）
  - FakeRedis 实现 task_service 实际用到的 6 个方法（xadd/get/set/expire/publish/xrange）

覆盖路径：
- create_task: 写 PG + xadd + 缓存
- get_task: Redis 命中 → 直接返回（不查 PG）
- get_task: Redis 未命中 → 查 PG + 回填缓存
- get_task: 都没有 → None
- update_task_state: PG 更新 + 缓存刷新；progress/result_uri/error 字段独立更新
- update_task_state: 不存在的 task_id → 返回 None
- publish_progress: xadd + publish + expire 同时发生
- get_event_history: xrange 反序列化 data 字段
- _cache_task_state: TTL 默认 3600
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.entities import Base
from app.services.tasks.task_service import (
    STREAM_DESIGN_GEN,
    TASK_STATE_COMPLETED,
    TASK_STATE_FAILED,
    TASK_STATE_PENDING,
    TASK_STATE_PROCESSING,
    TaskInfo,
    TaskService,
)


# ---- FakeRedis: 仅实现 task_service 用到的方法 -------------------------------


class FakeRedis:
    """In-memory Redis 替身。

    只实现 TaskService 实际调用的 6 个方法。够用即可——把 redis-py 整体替身在这里
    既会让测试变慢，又会让真实 bug（错用 API）被掩盖。
    """

    def __init__(self) -> None:
        # 简单 key-value 存储
        self.kv: Dict[str, str] = {}
        self.ttls: Dict[str, int] = {}
        # streams: {stream_name: [(entry_id, fields), ...]}
        self.streams: Dict[str, List[Tuple[str, Dict[str, str]]]] = {}
        # publish 调用历史：[(channel, message), ...]
        self.publishes: List[Tuple[str, str]] = []
        # 自增 entry id（满足 task_service 不关心格式只关心唯一性）
        self._next_id = 1

    async def get(self, key: str) -> Optional[str]:
        return self.kv.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> None:
        self.kv[key] = value
        if ex is not None:
            self.ttls[key] = ex

    async def expire(self, key: str, seconds: int) -> None:
        self.ttls[key] = seconds

    async def publish(self, channel: str, message: str) -> None:
        self.publishes.append((channel, message))

    async def xadd(
        self, stream: str, fields: dict, maxlen: Optional[int] = None
    ) -> str:
        entry_id = f"{self._next_id}-0"
        self._next_id += 1
        self.streams.setdefault(stream, []).append((entry_id, dict(fields)))
        if maxlen is not None and len(self.streams[stream]) > maxlen:
            self.streams[stream] = self.streams[stream][-maxlen:]
        return entry_id

    async def xrange(
        self, stream: str, min: str = "-", max: str = "+", count: Optional[int] = None
    ) -> List[Tuple[str, Dict[str, str]]]:
        entries = self.streams.get(stream, [])
        # task_service 用 last_event_id 做切片：min='-' 意味着全量；其他值表示从该 id 之后
        if min not in ("-", "0", "0-0"):
            # 取 id > min 的（task_service 期望的 Last-Event-ID 语义）
            entries = [e for e in entries if e[0] > min]
        if count is not None:
            entries = entries[:count]
        return list(entries)


# ---- fixtures ---------------------------------------------------------------


@pytest_asyncio.fixture
async def sqlite_session_maker(monkeypatch) -> AsyncIterator[Any]:
    """SQLite in-memory + 替换 task_service 模块全局的 async_session_maker。"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    monkeypatch.setattr(
        "app.services.tasks.task_service.async_session_maker", maker
    )
    yield maker
    await engine.dispose()


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture
def service(fake_redis: FakeRedis) -> TaskService:
    return TaskService(fake_redis)


# ---- create_task -------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_task_persists_to_pg_and_redis(
    service: TaskService, fake_redis: FakeRedis, sqlite_session_maker
):
    payload = {"task_type": "hunyuan3d", "prompt": "白瓷茶杯"}
    info = await service.create_task(payload)

    assert isinstance(info, TaskInfo)
    assert info.state == TASK_STATE_PENDING
    assert info.payload == payload
    assert info.task_id  # 自动生成

    # 1) PG 中能查到
    from sqlalchemy import select
    from app.models.entities import Task as TaskModel
    async with sqlite_session_maker() as s:
        row = (await s.execute(select(TaskModel).where(TaskModel.task_id == info.task_id))).scalar_one()
        assert row.state == TASK_STATE_PENDING
        assert row.payload == payload

    # 2) Stream 里有一条
    assert len(fake_redis.streams[STREAM_DESIGN_GEN]) == 1
    stream_fields = fake_redis.streams[STREAM_DESIGN_GEN][0][1]
    assert stream_fields["task_id"] == info.task_id
    assert json.loads(stream_fields["payload"]) == payload

    # 3) 缓存键存在 + TTL 默认 3600
    cached = json.loads(fake_redis.kv[f"task:{info.task_id}:state"])
    assert cached["state"] == TASK_STATE_PENDING
    assert fake_redis.ttls[f"task:{info.task_id}:state"] == 3600


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_task_uses_explicit_id(
    service: TaskService, fake_redis: FakeRedis, sqlite_session_maker
):
    info = await service.create_task({"k": "v"}, task_id="my-task-123")
    assert info.task_id == "my-task-123"
    assert f"task:my-task-123:state" in fake_redis.kv


# ---- get_task ----------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_task_hits_redis_cache_first(
    service: TaskService, fake_redis: FakeRedis, sqlite_session_maker
):
    """缓存命中时不应查 PG（性能关键路径）。"""
    info = await service.create_task({"x": 1})

    # 把 PG 那条删了，仍能从缓存读出
    from sqlalchemy import delete
    from app.models.entities import Task as TaskModel
    async with sqlite_session_maker() as s:
        await s.execute(delete(TaskModel).where(TaskModel.task_id == info.task_id))
        await s.commit()

    fetched = await service.get_task(info.task_id)
    assert fetched is not None
    assert fetched.state == TASK_STATE_PENDING


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_task_falls_back_to_pg_and_refills_cache(
    service: TaskService, fake_redis: FakeRedis, sqlite_session_maker
):
    """Redis miss 时查 PG，并把结果回填到缓存。"""
    info = await service.create_task({"x": 1})

    # 清缓存，模拟 cache miss
    fake_redis.kv.clear()

    fetched = await service.get_task(info.task_id)
    assert fetched is not None
    assert fetched.state == TASK_STATE_PENDING

    # 缓存应被回填
    assert f"task:{info.task_id}:state" in fake_redis.kv


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_task_returns_none_for_missing(
    service: TaskService, sqlite_session_maker
):
    assert await service.get_task("nonexistent") is None


# ---- update_task_state -------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_task_state_writes_pg_and_cache(
    service: TaskService, fake_redis: FakeRedis, sqlite_session_maker
):
    info = await service.create_task({"x": 1})

    updated = await service.update_task_state(
        info.task_id,
        TASK_STATE_PROCESSING,
        progress=50,
    )

    assert updated is not None
    assert updated.state == TASK_STATE_PROCESSING
    assert updated.progress == 50

    # PG 真正写入
    from sqlalchemy import select
    from app.models.entities import Task as TaskModel
    async with sqlite_session_maker() as s:
        row = (await s.execute(select(TaskModel).where(TaskModel.task_id == info.task_id))).scalar_one()
        assert row.state == TASK_STATE_PROCESSING
        assert row.progress == 50

    # 缓存刷新到新状态
    cached = json.loads(fake_redis.kv[f"task:{info.task_id}:state"])
    assert cached["state"] == TASK_STATE_PROCESSING
    assert cached["progress"] == 50


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_task_state_completed_with_result_uri(
    service: TaskService, sqlite_session_maker
):
    info = await service.create_task({"x": 1})

    updated = await service.update_task_state(
        info.task_id,
        TASK_STATE_COMPLETED,
        progress=100,
        result_uri="http://minio/result.glb",
    )

    assert updated.state == TASK_STATE_COMPLETED
    assert updated.result_uri == "http://minio/result.glb"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_task_state_failed_records_error(
    service: TaskService, sqlite_session_maker
):
    info = await service.create_task({"x": 1})
    updated = await service.update_task_state(
        info.task_id, TASK_STATE_FAILED, error_message="hunyuan3d 504"
    )
    assert updated.state == TASK_STATE_FAILED
    assert updated.error_message == "hunyuan3d 504"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_task_state_returns_none_when_missing(
    service: TaskService, sqlite_session_maker
):
    """不存在的 task_id 不应抛异常，返回 None 让上层决定（worker 常碰到孤儿 id）。"""
    assert await service.update_task_state("ghost", TASK_STATE_PROCESSING) is None


# ---- publish_progress + get_event_history ------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_progress_writes_stream_and_pubsub(
    service: TaskService, fake_redis: FakeRedis
):
    """xadd + publish 必须同时发生且共享同一 entry id（前端 SSE 去重依赖此）。"""
    await service.publish_progress("t-1", "progress", {"percent": 30})

    # Stream 写入
    stream_key = "task:t-1:events"
    assert stream_key in fake_redis.streams
    entry_id, fields = fake_redis.streams[stream_key][0]
    assert fields["type"] == "progress"
    assert json.loads(fields["data"]) == {"percent": 30}

    # Pub/Sub 投递
    assert len(fake_redis.publishes) == 1
    channel, body = fake_redis.publishes[0]
    assert channel == "task:t-1:progress"
    payload = json.loads(body)
    assert payload["id"] == entry_id  # 共享 id
    assert payload["data"] == {"percent": 30}

    # Stream TTL 1h
    assert fake_redis.ttls[stream_key] == 3600


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_event_history_returns_replayable_events(
    service: TaskService, fake_redis: FakeRedis
):
    await service.publish_progress("t-2", "progress", {"percent": 10})
    await service.publish_progress("t-2", "progress", {"percent": 50})
    await service.publish_progress("t-2", "completed", {"result_uri": "x"})

    history = await service.get_event_history("t-2")
    assert len(history) == 3
    assert history[0]["type"] == "progress"
    assert history[0]["data"] == {"percent": 10}
    assert history[2]["type"] == "completed"
    assert history[2]["data"] == {"result_uri": "x"}
    # id 字段透传，前端用来在 last-event-id 之后续传
    assert all("id" in e for e in history)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_event_history_filters_by_last_event_id(
    service: TaskService, fake_redis: FakeRedis
):
    """last_event_id 模拟 SSE 断线重连：只回放该 id 之后的事件。"""
    await service.publish_progress("t-3", "progress", {"percent": 10})
    await service.publish_progress("t-3", "progress", {"percent": 50})

    # 第一条的 id
    first_id = fake_redis.streams["task:t-3:events"][0][0]

    history = await service.get_event_history("t-3", last_event_id=first_id)
    assert len(history) == 1
    assert history[0]["data"] == {"percent": 50}


# ---- TaskInfo 数据契约 -------------------------------------------------------


@pytest.mark.unit
def test_task_info_to_dict_round_trip():
    info = TaskInfo(task_id="x", state="pending", payload={"a": 1}, progress=0)
    d = info.to_dict()
    assert d["task_id"] == "x"
    assert d["state"] == "pending"
    # to_dict 必须能 json.dumps（task_service 用它做缓存）
    assert json.dumps(d)
