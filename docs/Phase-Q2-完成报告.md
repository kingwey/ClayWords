# Phase Q2 完成报告

**日期**: 2026-06-21  
**状态**: ✅ 完成  
**耗时**: 约 1.5 小时

---

## 完成的任务

### Q2.1 Redis Streams + 任务队列 ✅

#### Q2.1.1 扩展 Redis 客户端 ✅
- [x] 扩展 `backend/app/core/redis.py` 支持完整的 Streams API
- [x] 新增 Consumer Group 操作（xgroup_create, xreadgroup, xack, xpending, xclaim）
- [x] 新增 Pub/Sub 高级操作（pubsub, publish, psubscribe）
- [x] 新增 Stream 范围查询（xrange, xlen）

#### Q2.1.2 创建任务服务层 ✅
- [x] 新文件 `backend/app/services/tasks/task_service.py`
- [x] `TaskService` 类完整实现：
  - `create_task()` - 三件事：PG 持久化 + Redis Stream 入队 + Redis 缓存
  - `get_task()` - 优先 Redis 缓存，fallback PostgreSQL
  - `update_task_state()` - 双写 Redis + PostgreSQL
  - `publish_progress()` - Pub/Sub + Stream 双发
  - `get_event_history()` - Last-Event-ID 重连支持

#### Q2.1.3 实现 Worker 消费者 ✅
- [x] 新文件 `backend/worker/consumer.py` - DesignWorker 完整实现
- [x] 新文件 `backend/worker/main.py` - 入口点
- [x] 功能特性：
  - Consumer Group 消费模式
  - 自动重试（max_retries=3）
  - Dead Letter 队列（design.gen.dead）
  - 卡死消息重新认领（claim_pending）
  - 优雅关闭（SIGTERM/SIGINT）
  - 进度上报集成

#### Q2.1.4 修改 Sessions API 使用任务队列 ✅
- [x] 修改 `backend/app/api/sessions.py`
- [x] 任务现在通过 TaskService 创建
- [x] 演示模式和正常模式都已迁移
- [x] 任务 ID 来自 TaskService（持久化保证）

### Q2.2 SSE 优化与持久化 ✅

#### Q2.2.1 SSE 票据改用 Redis ✅
- [x] 修改 `backend/app/api/sse.py`
- [x] 票据存储在 Redis（key=`sse:ticket:{uuid}`，TTL 60s）
- [x] 多实例部署兼容
- [x] 一次性删除（一票一用）

#### Q2.2.2 SSE 事件流改用 Redis Pub/Sub ✅
- [x] 完全重写 `backend/app/api/tasks.py`
- [x] `pubsub.psubscribe(f"task:{task_id}:*")` 订阅任务事件
- [x] 1 秒 keepalive 心跳
- [x] 终态事件（done/error）自动断开

#### Q2.2.3 支持 Last-Event-ID 重连 ✅
- [x] SSE 端点支持 `Last-Event-ID` header
- [x] 服务端用 `XRANGE task:{id}:events <last-id> +` 回放
- [x] 事件流双写：Pub/Sub（实时）+ Stream（重连）
- [x] 事件流 TTL 1 小时自动清理

---

## 验证结果

### 单元测试：8/8 通过

```
=== Phase Q2 Verification ===

Testing Redis connection... [OK] Redis connected
Testing Redis Streams... [OK] Streams working (1 entries)
Testing Consumer Group... [OK] Consumer Group working
Testing TaskService.create_task... [OK] Task created
Testing task state transitions... [OK] State transitions working
Testing Pub/Sub progress... [OK] Pub/Sub working (2 events)
Testing event history replay... [OK] Event history working (4 events)
Testing SSE tickets in Redis... [OK] SSE tickets working

=== Summary ===
Passed: 8/8
```

### 端到端 Worker 测试：通过

```
=== Worker End-to-End Test ===

[1/4] Starting worker in background...
[2/4] Submitting test task...
     Task ID: <uuid>
[3/4] Waiting for worker to process...
     [OK] Task completed in 2.0s
     Result: mock://result/<task_id>
[4/4] Stopping worker...

[OK] End-to-end test passed!
```

---

## 关键架构

### 任务流程

```
Client → POST /sessions/{id}/messages
         ↓
     TaskService.create_task()
         ↓
   ┌─────┴────────────────────┐
   │                          │
PostgreSQL              Redis Stream (design.gen)
(durability)            (queue)
                              ↓
                        Worker (XREADGROUP)
                              ↓
                        process_task()
                              ↓
                    ┌─────────┴──────────┐
                    │                     │
              Pub/Sub               Event Stream
              (实时)                  (回放)
                    │                     │
                    ▼                     │
              SSE Client ◄────────────────┘
                              (Last-Event-ID 重连)
```

### Redis Key/Stream 结构

| Key/Stream | 用途 | TTL |
|-----------|------|-----|
| `design.gen` | 任务队列 Stream | persistent |
| `design.gen.dead` | 失败任务 Dead Letter | persistent |
| `task:{id}:state` | 任务状态缓存 | 3600s |
| `task:{id}:events` | 事件流（重连用） | 3600s |
| `task:{id}:{event_type}` | Pub/Sub 频道 | - |
| `sse:ticket:{uuid}` | SSE 票据 | 60s |

### 状态机

```
pending → processing → completed
              ↓
            failed (after 3 retries → dead letter)
```

---

## 文件清单

### 修改的文件
- `backend/app/core/redis.py` - 扩展为完整 Streams 客户端
- `backend/app/api/sse.py` - 票据改用 Redis
- `backend/app/api/tasks.py` - 完全重写，使用 Redis Pub/Sub
- `backend/app/api/sessions.py` - 使用 TaskService 创建任务
- `backend/app/main.py` - 启动时连接 Redis
- `backend/worker/__init__.py` - 模块标识

### 新增的文件
- `backend/app/services/tasks/__init__.py`
- `backend/app/services/tasks/task_service.py` - 任务服务核心
- `backend/worker/consumer.py` - Worker 消费者
- `backend/worker/main.py` - Worker 入口
- `scripts/verify_q2.py` - Phase Q2 验证脚本
- `scripts/test_worker_e2e.py` - 端到端测试

---

## 使用说明

### 启动 Worker
```bash
cd backend
python -m worker.main
```

### Worker 参数（自定义）
```python
from worker.consumer import DesignWorker
from app.core.redis import redis_client

worker = DesignWorker(
    redis=redis_client,
    stream="design.gen",
    group="design.gen.workers",
    consumer_name="worker-1",
    max_retries=3,
    block_ms=5000,
    idle_threshold_ms=300000,
)
```

### 提交任务
```python
from app.services.tasks.task_service import get_task_service

task_service = await get_task_service()
task = await task_service.create_task(
    payload={
        "session_id": "...",
        "user_id": "...",
        "content": "make a ceramic vase"
    }
)
print(task.task_id)
```

### SSE 客户端连接
```javascript
// 1. 获取票据
const { ticket } = await fetch('/api/v1/sse/tickets', {
  method: 'POST',
  headers: { Authorization: 'Bearer ...' }
}).then(r => r.json());

// 2. 连接 SSE
const evtSource = new EventSource(
  `/api/v1/tasks/${taskId}/events?ticket=${ticket}`
);

evtSource.addEventListener('progress', (e) => {
  const data = JSON.parse(e.data);
  console.log('Progress:', data);
});

evtSource.addEventListener('done', (e) => {
  console.log('Done:', JSON.parse(e.data));
  evtSource.close();
});
```

### 测试 Worker 重启恢复
```bash
# Terminal 1: 启动 worker
python -m worker.main

# Terminal 2: 提交任务
python scripts/test_worker_e2e.py

# Terminal 1: Ctrl+C 杀掉 worker

# Terminal 1: 重启 worker
python -m worker.main
# Worker 会自动认领 pending 列表中的任务
```

---

## 关键技术点

### 1. 双写策略（Redis + PostgreSQL）
- **写**: 先 PG 持久化 → 再 Redis 缓存 + Stream 入队
- **读**: 优先 Redis 缓存 → fallback PG → 回填缓存
- **优势**: 高性能 + 数据安全 + Redis 重启自恢复

### 2. Consumer Group 模式
- **多 Worker 并发**: 每个 Worker 独立消费，无重复处理
- **故障恢复**: 卡死消息可被其他 Worker 认领
- **负载均衡**: Redis 自动分发任务

### 3. Pub/Sub + Stream 双发布
- **Pub/Sub**: 实时推送，无延迟
- **Stream**: 持久化记录，支持回放
- **Last-Event-ID 重连**: 客户端断网 30s 重连不丢事件

### 4. 优雅关闭
- 信号处理（SIGTERM/SIGINT）
- 当前任务处理完才退出
- 未 ACK 的任务保留在 pending 列表

---

## 风险与缓解

### 已实现的容错
✅ Worker 崩溃 → 任务保留在 pending，下次启动自动重试  
✅ Redis 宕机 → 任务状态从 PG 恢复  
✅ 任务失败 → 自动重试 3 次后入 Dead Letter  
✅ 客户端断网 → Last-Event-ID 重连不丢事件  
✅ SSE 连接超时 → 1 秒 keepalive 心跳  

### 已知限制
⚠️ Nginx 配置（Q2.2.3 第三步）尚未编写  
⚠️ 真实任务处理逻辑（连接 LLM/3D 生成）待 Phase Q3  
⚠️ Worker 性能监控（Prometheus）待 Phase Q7  

---

## 后续接口

### 为 Phase Q3 准备（3D 真模型）
- Worker 框架已就绪，handler 接口已定义
- 进度上报机制完善（25%/50%/75%/100%）
- 可接入 Hunyuan3D-2 + trimesh 管道

### 为 Phase Q7 准备（可观测性）
- Worker 已支持 logging
- 任务状态可埋点（pending/processing/completed/failed 计数）
- 队列长度可暴露（xlen）

---

## 总结

Phase Q2 成功将任务队列和 SSE 系统从内存升级到 Redis Streams + Pub/Sub。核心成果：

✅ **任务持久化** - 双写 Redis + PostgreSQL  
✅ **Worker 框架** - Consumer Group + 自动重试 + Dead Letter  
✅ **SSE 实时推送** - Pub/Sub 即时 + Stream 重连  
✅ **多实例兼容** - 票据全局共享  
✅ **测试覆盖** - 8 单元测试 + 端到端测试全部通过  

**下一步**: Phase Q3 - 3D 真模型与模板库（最重头戏）
