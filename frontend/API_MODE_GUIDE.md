# 前端 API 模式切换说明

## 环境变量配置

前端支持两种模式：

### 1. 真实 API 模式（默认）✅

使用 `.env` 文件（已创建）：
```env
VITE_USE_REAL_API=true
```

**要求**：
- 后端服务运行在 `http://localhost:8000`
- PostgreSQL 数据库已启动
- Redis 已启动（用于任务队列）
- 通义千问 API Key 已配置

**使用场景**：
- 开发联调
- 测试真实 LLM 生成
- 完整功能测试

### 2. Mock 模式

复制 `.env.mock` 为 `.env`：
```bash
cp .env.mock .env
```

或手动修改 `.env`：
```env
VITE_USE_REAL_API=false
```

**特点**：
- 纯前端模拟，不需要后端服务
- 返回硬编码的三个演示方案
- 适合前端开发和演示

## 快速切换

### 切换到真实 API：
```bash
cd frontend
echo "VITE_USE_REAL_API=true" > .env
npm run dev
```

### 切换到 Mock 模式：
```bash
cd frontend
echo "VITE_USE_REAL_API=false" > .env
npm run dev
```

## Vite 代理配置

前端通过 Vite 代理转发 API 请求到后端：

```typescript
// vite.config.ts
server: {
  port: 5173,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',  // 后端地址
      changeOrigin: true
    }
  }
}
```

**流程**：
1. 前端请求 `/api/v1/sessions`
2. Vite 代理转发到 `http://localhost:8000/api/v1/sessions`
3. 后端处理并返回结果

## 启动步骤

### 真实 API 模式完整启动：

#### 1. 启动后端服务
```bash
cd backend
# 确保环境变量配置正确（.env）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 2. 启动前端
```bash
cd frontend
# 确保 .env 中 VITE_USE_REAL_API=true
npm run dev
```

#### 3. 访问
浏览器打开：http://localhost:5173

### Mock 模式启动：

```bash
cd frontend
# 确保 .env 中 VITE_USE_REAL_API=false
npm run dev
```

浏览器打开：http://localhost:5173（无需后端）

## 调试技巧

### 查看实际使用的模式
打开浏览器控制台，查看启动信息或网络请求：
- 真实 API 模式：会看到 `/api/v1/sessions` 等请求
- Mock 模式：只有本地 setTimeout 模拟

### 强制刷新环境变量
修改 `.env` 后需要重启开发服务器：
```bash
# Ctrl+C 停止
npm run dev  # 重新启动
```

## 故障排查

### 真实 API 模式报错

**错误**：`Failed to create session` 或 `网络请求失败`

**原因**：
- 后端服务未启动
- 数据库连接失败
- Redis 未启动

**解决**：
1. 检查后端是否运行：`curl http://localhost:8000/health`
2. 检查数据库：`psql -U claywords -d claywords -c "SELECT 1;"`
3. 检查 Redis：`redis-cli ping`

### Mock 模式无响应

**原因**：环境变量未生效

**解决**：
1. 确认 `.env` 文件存在且内容正确
2. 重启 Vite 开发服务器
3. 清除浏览器缓存

## 技术实现

### 真实 API 流程

```
用户输入 
  → sendUserMessage() 
  → sessionsApi.sendMessage() 
  → 后端 LLM 解析 
  → 创建任务 
  → 前端轮询任务状态 
  → 返回设计方案
```

### Mock 流程

```
用户输入 
  → sendUserMessageMock() 
  → setTimeout 模拟延迟 
  → 返回硬编码方案
```

---

**当前配置**：真实 API 模式 ✅

修改模式后记得重启开发服务器！
