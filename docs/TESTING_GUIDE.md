# ClayWords 对话功能测试指南

## 系统架构

```
用户输入
  ↓
前端 (Vue3 + Vite)
  ↓ HTTP POST /api/v1/sessions/{id}/messages
后端 API (FastAPI)
  ↓ 创建任务 → Redis Streams
Worker 消费者
  ↓ 调用 LLM 解析 + 生成方案
  ↓ 更新任务状态 → PostgreSQL + Redis
  ↓ 发布进度事件 → Redis Pub/Sub
前端轮询/SSE
  ↓ 获取结果
显示方案
```

## 启动步骤（完整模式）

### 1. 确保依赖服务运行

```bash
# PostgreSQL（端口 5432）
# Redis（端口 6379）
# MinIO（端口 9000）- 可选

# 快速检查
redis-cli ping  # 应返回 PONG
psql -U claywords -d claywords -c "SELECT 1;"  # 应返回 1
```

### 2. 启动后端 API

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**验证**：访问 http://localhost:8000/health 应返回 `{"status":"ok"}`

### 3. 启动 Worker（重要！）

**新开一个终端窗口**，运行：

```bash
cd backend
python -m worker.main
```

**或者在 Windows 上双击**：
```
start_worker.bat
```

**成功标志**：
```
============================================================
ClayWords Worker Starting...
============================================================
2026-06-24 18:40:22 [INFO] Worker initialized: stream=design.gen, group=design.gen.workers
2026-06-24 18:40:22 [INFO] Worker starting consumer loop
```

### 4. 启动前端

```bash
cd frontend
npm run dev
```

访问：http://localhost:5173

---

## 测试流程

### 1. 输入测试消息

在对话框中输入：
```
送给妈妈的生日礼物，她属兔，喜欢月亮和桂花，希望是冷白釉，放玄关
```

### 2. 观察后端日志

**API 日志**（终端 1）：
```
INFO: POST /api/v1/sessions/{session_id}/messages
INFO: Task created: 3bfb9cfd-47e0-46be-9344-3d4d0186f73f
```

**Worker 日志**（终端 2）：
```
INFO: Processing task: 3bfb9cfd-47e0-46be-9344-3d4d0186f73f
INFO: Calling LLM parser...
INFO: Task completed: 3bfb9cfd-47e0-46be-9344-3d4d0186f73f
```

### 3. 前端状态变化

应该看到：
1. "陶语 · 正在分析" - LLM 解析参数
2. "陶语 · 正在处理" - Worker 处理任务
3. "陶语 · 方案生成完成" - 显示 3 个方案
4. 右侧显示可选方案卡片

---

## 常见问题排查

### 问题 1：前端一直显示"正在处理"，轮询不停止

**症状**：
- 后端日志显示：`GET /api/v1/tasks/{task_id}` 持续 200 OK
- 任务状态一直是 `pending`

**原因**：Worker 未启动

**解决**：
```bash
cd backend
python -m worker.main
```

### 问题 2：Worker 启动失败

**症状**：
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**原因**：Redis 未启动

**解决**：
```bash
# Windows (使用 WSL 或独立安装)
redis-server

# 或检查 Redis 是否运行
redis-cli ping
```

### 问题 3：任务状态变成 `failed`

**查看错误**：
```bash
# 查看后端日志
# 或访问 http://localhost:8000/api/v1/tasks/{task_id}
# 查看 error 字段
```

**常见原因**：
1. **LLM API Key 未配置**
   - 检查 `backend/.env` 中 `TONGYI_API_KEY` 或 `OPENAI_API_KEY`
   - Worker 会自动降级到 mock 模式

2. **数据库连接失败**
   - 检查 PostgreSQL 是否运行
   - 检查 `DATABASE_URL` 配置

### 问题 4：前端报错 "Failed to create session"

**原因**：后端 API 未启动或无法连接

**检查**：
```bash
curl http://localhost:8000/health
# 应返回 {"status":"ok"}
```

---

## 演示模式（不需要 Worker）

如果不想启动 Worker，可以使用演示模式：

### 方式 1：后端演示模式

前端代码已修改为自动使用 `demo=true` 参数：

```typescript
// useDesignMessagesReal.ts
const { data } = await sessionsApi.sendMessage(sessionId.value, prompt, true)
```

后端会直接返回预定义的演示方案，不经过任务队列。

### 方式 2：纯前端 Mock

修改 `frontend/.env`：
```env
VITE_USE_REAL_API=false
```

完全使用前端模拟数据，不调用后端。

---

## 性能监控

### 查看任务队列状态

```bash
redis-cli XLEN design.gen  # 队列长度
redis-cli XINFO GROUPS design.gen  # 消费者组信息
```

### 查看任务状态

```bash
curl http://localhost:8000/api/v1/tasks/{task_id}
```

### 数据库查询

```sql
-- 查看最近的任务
SELECT task_id, state, created_at, updated_at 
FROM tasks 
ORDER BY created_at DESC 
LIMIT 10;

-- 查看会话
SELECT session_id, title, created_at 
FROM sessions 
ORDER BY created_at DESC 
LIMIT 10;
```

---

## 架构说明

### 为什么需要 Worker？

**异步任务处理**：
- LLM 调用可能需要 2-10 秒
- 阻塞 HTTP 请求会影响用户体验
- Worker 异步处理，API 立即返回 task_id

**可扩展性**：
- 可以启动多个 Worker 并行处理
- Redis Streams 自动负载均衡
- 支持水平扩展

**容错性**：
- 任务持久化到 PostgreSQL
- Redis Streams 支持重试
- Worker 崩溃后其他 Worker 可以接管

### 数据流

1. **创建任务**：
   - API → PostgreSQL（持久化）
   - API → Redis Streams（队列）
   - API → Redis Cache（快速查询）

2. **处理任务**：
   - Worker → Redis Streams（消费）
   - Worker → LLM API（解析）
   - Worker → PostgreSQL（更新状态）
   - Worker → Redis Cache（更新缓存）
   - Worker → Redis Pub/Sub（发布进度）

3. **查询状态**：
   - 前端 → API → Redis Cache（优先）
   - 前端 → API → PostgreSQL（降级）

---

## 当前配置

- ✅ 前端：真实 API 模式（`VITE_USE_REAL_API=true`）
- ✅ 后端：LLM 已配置（通义千问 + OpenAI）
- ✅ 演示模式：已启用（`demo=true`）

**推荐启动方式**：

1. 快速演示：只启动后端 API（使用 demo 模式）
2. 完整测试：启动后端 API + Worker（真实 LLM）

---

**需要帮助？** 查看日志输出或联系开发团队。
