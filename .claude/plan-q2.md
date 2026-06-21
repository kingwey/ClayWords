# Phase Q2 实施计划：队列与 SSE 落到 Redis Streams

## 概述
将任务队列从内存迁移到 Redis Streams，实现可持久化、可重放的任务处理系统，并优化 SSE 连接管理。

## 当前状态分析

### 已有基础
- ✅ Redis 客户端基础封装 (`app/core/redis.py`)
- ✅ 基础 SSE 实现 (`app/api/sse.py`)
- ✅ 任务状态 API (`app/api/tasks.py`)
- ✅ `tasks` 表已创建（Phase Q1）

### 现有问题
- ❌ 任务状态存储在内存 (`_task_status`, `_task_options`, `_task_events`)
- ❌ SSE 票据存储在内存 (`_ticket_store`)
- ❌ Worker 未实现（`backend/worker/` 仅占位）
- ❌ 无任务队列，任务无法异步处理
- ❌ 重启后所有状态丢失
- ❌ 无法横向扩展（多实例冲突）

## 实施步骤

### Q2.1 Redis Streams + 任务队列

#### Q2.1.1 扩展 Redis 客户端
**文件**: `backend/app/core/redis.py`

**新增方法**:
```python
# Consumer Group 相关
async def xgroup_create(self, stream: str, group: str, id: str = '0', mkstream: bool = True)
async def xreadgroup(self, group: str, consumer: str, streams: dict, count: int = None, block: int = None)
async def xack(self, stream: str, group: str, *ids)
async def xpending(self, stream: str, group: str)
async def xclaim(self, stream: str, group: str, consumer: str, min_idle_time: int, *ids)

# Pub/Sub 相关（已有 publish）
async def subscribe(self, *channels)
async def psubscribe(self, *patterns)
```

#### Q2.1.2 创建任务服务层
**新文件**: `backend/app/services/tasks/task_service.py`

**功能**:
1. 任务生命周期管理
   - `create_task()` - 创建任务并写入 Redis Streams + Postgres
   - `get_task()` - 从 Redis 读取，fallback 到 Postgres
   - `update_task()` - 更新状态到 Redis + Postgres
   - `publish_progress()` - 发布进度到 Redis Pub/Sub

2. Redis Streams 结构
   ```
   Stream: design.gen
   Fields: {
     task_id: uuid,
     session_id: uuid,
     user_id: uuid,
     payload: json,
     created_at: timestamp
   }
   
   Consumer Group: design.gen.workers
   Dead Letter: design.gen.dead
   ```

3. 状态机
   ```
   pending → processing → completed/failed
   ```

#### Q2.1.3 实现 Worker 消费者
**新文件**: `backend/worker/consumer.py`

**功能**:
1. 启动 Consumer Group 消费者
2. `XREADGROUP` 从 `design.gen` 读取任务
3. 处理任务（调用生成管道）
4. `XACK` 确认处理完成
5. 异常处理：
   - 超过 3 次重试 → 移到 `design.gen.dead`
   - 发送告警

**新文件**: `backend/worker/main.py`

**功能**:
```python
import asyncio
from worker.consumer import DesignWorker

async def main():
    worker = DesignWorker(
        redis_url=settings.REDIS_URL,
        stream='design.gen',
        group='design.gen.workers',
        consumer_name=f'worker-{uuid.uuid4()}'
    )
    await worker.run()

if __name__ == '__main__':
    asyncio.run(main())
```

#### Q2.1.4 修改 Sessions API 使用队列
**修改文件**: `backend/app/api/sessions.py`

**修改点**:
```python
# 原来：直接返回 task_id
task_id = str(uuid.uuid4())
return SendMessageResponse(task_id=task_id)

# 改为：创建任务并入队
from app.services.tasks.task_service import TaskService
task_service = TaskService()

task = await task_service.create_task(
    session_id=session_id,
    user_id=current_user.user_id,
    payload={
        'content': request.content,
        'design_params': user_message.design_params
    }
)

return SendMessageResponse(task_id=task.task_id)
```

### Q2.2 SSE 优化与持久化

#### Q2.2.1 SSE 票据改用 Redis
**修改文件**: `backend/app/api/sse.py`

**修改点**:
```python
# 原来：内存字典
_ticket_store: Dict[str, tuple[str, datetime]] = {}

# 改为：Redis
@router.post("/tickets", response_model=TicketResponse)
async def create_ticket(
    current_user: UserInfo = Depends(get_current_user),
    redis: RedisClient = Depends(get_redis)
):
    ticket = str(uuid.uuid4())
    key = f"sse:ticket:{ticket}"
    await redis.set(key, current_user.user_id, ex=60)  # 60s TTL
    return TicketResponse(ticket=ticket, expires_in=60)

async def validate_ticket(ticket: str, redis: RedisClient) -> str:
    key = f"sse:ticket:{ticket}"
    user_id = await redis.get(key)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired ticket")
    await redis.delete(key)  # 一次性删除
    return user_id.decode()
```

#### Q2.2.2 SSE 事件流改用 Redis Pub/Sub
**修改文件**: `backend/app/api/tasks.py`

**修改点**:
```python
# 原来：内存 Queue
_task_events: Dict[str, asyncio.Queue] = {}

# 改为：Redis Pub/Sub
@router.get("/{task_id}/events")
async def stream_task_events(
    task_id: str,
    ticket: str = Query(...),
    current_user: UserInfo = Depends(get_current_user),
    redis: RedisClient = Depends(get_redis)
):
    # 验证票据
    ticket_user_id = await validate_ticket(ticket, redis)
    if ticket_user_id != current_user.user_id:
        raise HTTPException(status_code=403)

    async def event_generator():
        # 订阅任务进度频道
        pubsub = redis.pubsub()
        await pubsub.psubscribe(f"task:{task_id}:*")
        
        yield f"event: connected\ndata: {json.dumps({'task_id': task_id})}\n\n"
        
        try:
            async for message in pubsub.listen():
                if message['type'] == 'pmessage':
                    event_type = message['channel'].split(':')[-1]
                    data = json.loads(message['data'])
                    yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
                    
                    if event_type in ('done', 'error'):
                        break
        finally:
            await pubsub.unsubscribe()
    
    return StreamingResponse(...)
```

#### Q2.2.3 支持 Last-Event-ID 重连
**修改文件**: `backend/app/api/tasks.py`

**新增功能**:
```python
@router.get("/{task_id}/events")
async def stream_task_events(
    task_id: str,
    ticket: str = Query(...),
    last_event_id: Optional[str] = Header(None, alias="Last-Event-ID"),
    ...
):
    async def event_generator():
        # 如果有 last_event_id，先回放历史事件
        if last_event_id:
            # 从 Redis Stream 读取历史事件
            events = await redis.xrange(
                f"task:{task_id}:events",
                last_event_id,
                '+'
            )
            for event_id, event_data in events:
                yield f"id: {event_id}\nevent: {event_data['type']}\ndata: {event_data['data']}\n\n"
        
        # 订阅新事件
        pubsub = redis.pubsub()
        await pubsub.psubscribe(f"task:{task_id}:*")
        ...
```

**进度发布改为双写**:
```python
# Worker 发布进度时
async def publish_progress(task_id: str, event_type: str, data: dict):
    # 1. 发布到 Pub/Sub（实时）
    await redis.publish(f"task:{task_id}:{event_type}", json.dumps(data))
    
    # 2. 写入 Stream（重连回放）
    await redis.xadd(
        f"task:{task_id}:events",
        {
            'type': event_type,
            'data': json.dumps(data),
            'timestamp': datetime.utcnow().isoformat()
        }
    )
    
    # 3. 设置 TTL（1小时后自动清理）
    await redis.expire(f"task:{task_id}:events", 3600)
```

### Q2.3 任务持久化与故障恢复

#### Q2.3.1 任务状态双写
**文件**: `backend/app/services/tasks/task_service.py`

**实现**:
```python
async def update_task_status(self, task_id: str, status: str, result: dict = None):
    # 1. 更新 Redis（快速读取）
    await self.redis.set(
        f"task:{task_id}:status",
        json.dumps({'status': status, 'result': result}),
        ex=3600
    )
    
    # 2. 更新 Postgres（持久化）
    async with async_session_maker() as session:
        stmt = select(Task).where(Task.task_id == task_id)
        result = await session.execute(stmt)
        task = result.scalar_one_or_none()
        
        if task:
            task.state = status
            task.updated_at = datetime.utcnow()
            if result:
                task.result_uri = result.get('uri')
                task.progress = result.get('progress', 0)
            await session.commit()
```

#### Q2.3.2 Worker 重启恢复
**文件**: `backend/worker/consumer.py`

**实现**:
```python
async def handle_pending_tasks(self):
    """处理 pending 列表中的任务（重启恢复）"""
    pending = await self.redis.xpending(self.stream, self.group)
    
    for entry in pending:
        task_id = entry['message_id']
        idle_time = entry['idle']
        
        # 超过 5 分钟未确认，重新认领
        if idle_time > 300000:  # 5 min in ms
            claimed = await self.redis.xclaim(
                self.stream,
                self.group,
                self.consumer_name,
                300000,
                task_id
            )
            
            for msg_id, msg_data in claimed:
                await self.process_task(msg_data)
```

## 依赖关系

```
Q2.1.1 (Redis 客户端) ──┐
                        ├──> Q2.1.2 (任务服务) ──> Q2.1.3 (Worker) ──> Q2.1.4 (Sessions API)
                        │                               │
Q2.2.1 (SSE 票据) ──────┤                               │
                        │                               │
Q2.2.2 (SSE Pub/Sub) ───┴───────────────────────────────┘
                                    │
                                    └──> Q2.2.3 (Last-Event-ID)
                                            │
                                            └──> Q2.3 (持久化 + 恢复)
```

## 测试策略

### 单元测试
- [ ] `test_redis_streams.py` - Redis Streams CRUD
- [ ] `test_task_service.py` - 任务服务层
- [ ] `test_sse_tickets.py` - SSE 票据生成和验证

### 集成测试
- [ ] `test_task_queue.py` - 任务入队、消费、确认
- [ ] `test_worker_recovery.py` - Worker 重启后恢复
- [ ] `test_sse_reconnect.py` - SSE 断线重连

### 压测
- [ ] 200 并发 SSE 连接保持 5 分钟
- [ ] 100 任务/秒入队速率

## 时间估算

| 任务 | 预计时间 | 优先级 |
|------|----------|--------|
| Q2.1.1 | 1h | P0 |
| Q2.1.2 | 3h | P0 |
| Q2.1.3 | 4h | P0 |
| Q2.1.4 | 1h | P0 |
| Q2.2.1 | 1h | P0 |
| Q2.2.2 | 2h | P0 |
| Q2.2.3 | 2h | P0 |
| Q2.3 | 2h | P0 |
| 测试编写 | 4h | P0 |
| **总计** | **20h** | **约 2.5 工作日** |

## 验收标准

### 最终验收清单
- [ ] 任务入队到 Redis Streams `design.gen`
- [ ] Worker 消费任务并 ACK
- [ ] 重启 Worker 后自动恢复 pending 任务
- [ ] SSE 票据存储在 Redis，TTL 60s
- [ ] SSE 通过 Redis Pub/Sub 推送进度
- [ ] 支持 Last-Event-ID 重连，不丢事件
- [ ] 任务状态双写 Redis + Postgres
- [ ] Redis 宕机后从 Postgres 恢复任务状态
- [ ] 多 Worker 实例并发消费不冲突
- [ ] Dead letter 队列捕获失败任务

## 风险与缓解

### 风险 1: Redis Streams 学习曲线
**缓解**: 参考 Redis 官方文档和社区最佳实践

### 风险 2: SSE 连接稳定性
**缓解**: 
- Nginx 配置正确（proxy_buffering off）
- 定期 keepalive 心跳
- 客户端自动重连机制

### 风险 3: Worker 处理速度
**缓解**:
- 横向扩展多个 Worker 实例
- 监控队列长度，自动告警

## 后续工作接口

完成 Q2 后，为 Q3（3D 真模型）准备：
- 任务队列已就绪，可接入真实 3D 生成管道
- 进度上报机制完善，可实时显示生成进度
- Worker 框架完成，可扩展多种任务类型
