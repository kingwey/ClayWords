# Hunyuan3D 接入部署指南

## 一、完成内容

### 1.1 代码文件

| 文件 | 说明 | 状态 |
|------|------|------|
| `app/core/config.py` | 新增 5 个配置项 | ✅ |
| `app/services/hunyuan3d/schemas.py` | 请求/响应数据模型 | ✅ |
| `app/services/hunyuan3d/client.py` | API 客户端 | ✅ |
| `app/services/hunyuan3d/worker.py` | 后台轮询 worker | ✅ |
| `app/api/hunyuan3d.py` | REST 端点 | ✅ |
| `app/main.py` | 路由注册 | ✅ |
| `scripts/test_hunyuan3d.py` | 测试脚本 | ✅ |

### 1.2 功能特性

- ✅ 支持文本 Prompt 和图片输入
- ✅ 支持 Model 3.0 / 3.1
- ✅ 异步任务管理（复用现有 Task 表）
- ✅ 后台轮询机制（每 5 秒查询一次）
- ✅ 超时保护（15 分钟）
- ✅ 功能开关（ENABLE_HUNYUAN3D）
- ✅ 详细日志记录（structlog）
- ⏸ MinIO 存储集成（待补充，当前返回原始 URL）

---

## 二、环境配置

### 2.1 添加环境变量

在 `.env` 文件中添加（**已提供的 API Key**）：

```bash
# Hunyuan3D 配置
HUNYUAN3D_API_KEY=sk-*******Ycr7j
HUNYUAN3D_BASE_URL=https://api.ai3d.cloud.tencent.com
HUNYUAN3D_POLL_INTERVAL=5
HUNYUAN3D_MAX_POLL_ATTEMPTS=120
ENABLE_HUNYUAN3D=true
```

⚠️ **安全提醒**: 
- API Key 已在对话中暴露，建议在腾讯云控制台 **立即 rotate**
- 生产环境使用密钥管理服务（如 Vault）

### 2.2 验证配置

```bash
cd backend
python -c "from app.core.config import settings; print(f'API Key: {settings.HUNYUAN3D_API_KEY[:10]}...')"
```

预期输出：
```
API Key: sk-*******...
```

---

## 三、本地测试

### 3.1 测试 API 连通性

```bash
cd backend
python scripts/test_hunyuan3d.py
```

**预期输出**:
```
============================================================
测试 Hunyuan3D API - 文本生成 3D
============================================================
✓ API Key 已配置: sk-*******...
✓ Base URL: https://api.ai3d.cloud.tencent.com

提交任务: {'Prompt': '一只可爱的小狗', 'Model': '3.0'}
✓ 任务已提交，JobId: 1387416933258346496

开始轮询任务状态（最多 10 分钟）...

[1/120] 状态: running       进度:  10%
[2/120] 状态: running       进度:  50%
[3/120] 状态: completed     进度: 100%

============================================================
✓ 生成完成！
结果 URL: https://...
============================================================
```

### 3.2 启动后端服务

```bash
# 终端 1: 启动 FastAPI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 终端 2: 启动轮询 worker
python -m app.services.hunyuan3d.worker
```

### 3.3 调用 REST API

```bash
# 1. 获取用户 Token（假设已登录）
TOKEN="your_jwt_token"

# 2. 提交 3D 生成任务
curl -X POST http://localhost:8000/api/v1/hunyuan3d/submit \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "Prompt": "一只可爱的小狗",
    "Model": "3.0"
  }'

# 响应示例:
# {
#   "task_id": "abc-123-def",
#   "job_id": "1387416933258346496",
#   "status": "pending",
#   "message": "3D 生成任务已提交..."
# }

# 3. 查询任务状态
curl http://localhost:8000/api/v1/tasks/abc-123-def \
  -H "Authorization: Bearer $TOKEN"

# 响应示例 (running):
# {
#   "task_id": "abc-123-def",
#   "status": "running",
#   "progress": 50,
#   "result_uri": null
# }

# 响应示例 (completed):
# {
#   "task_id": "abc-123-def",
#   "status": "completed",
#   "progress": 100,
#   "result_uri": "https://..."
# }
```

---

## 四、生产部署

### 4.1 Systemd 服务配置

**FastAPI 服务** (`/etc/systemd/system/claywords-api.service`):
```ini
[Unit]
Description=ClayWords FastAPI Backend
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=claywords
WorkingDirectory=/opt/claywords/backend
EnvironmentFile=/opt/claywords/.env
ExecStart=/opt/claywords/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

**Hunyuan3D Worker** (`/etc/systemd/system/claywords-hunyuan3d-worker.service`):
```ini
[Unit]
Description=ClayWords Hunyuan3D Polling Worker
After=network.target redis.service

[Service]
Type=simple
User=claywords
WorkingDirectory=/opt/claywords/backend
EnvironmentFile=/opt/claywords/.env
ExecStart=/opt/claywords/venv/bin/python -m app.services.hunyuan3d.worker
Restart=always

[Install]
WantedBy=multi-user.target
```

**启动服务**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable claywords-api claywords-hunyuan3d-worker
sudo systemctl start claywords-api claywords-hunyuan3d-worker

# 查看状态
sudo systemctl status claywords-hunyuan3d-worker
sudo journalctl -u claywords-hunyuan3d-worker -f
```

### 4.2 Docker Compose 配置

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    environment:
      - HUNYUAN3D_API_KEY=${HUNYUAN3D_API_KEY}
      - ENABLE_HUNYUAN3D=true
    # ...

  hunyuan3d-worker:
    build: ./backend
    command: python -m app.services.hunyuan3d.worker
    environment:
      - HUNYUAN3D_API_KEY=${HUNYUAN3D_API_KEY}
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - postgres
      - redis
    restart: always
```

**启动**:
```bash
docker-compose up -d hunyuan3d-worker
docker-compose logs -f hunyuan3d-worker
```

---

## 五、监控与告警

### 5.1 日志监控

```bash
# 查看轮询日志
tail -f /var/log/claywords/hunyuan3d-worker.log | grep hunyuan3d

# 关键日志事件:
# - hunyuan3d_submit: 任务提交
# - hunyuan3d_task_running: 任务进行中
# - hunyuan3d_task_completed: 任务完成
# - hunyuan3d_task_failed: 任务失败
# - hunyuan3d_download_failed: 3D 文件下载失败
```

### 5.2 业务指标

在现有 Prometheus metrics 中添加 Hunyuan3D 指标：

```python
# app/core/metrics.py
hunyuan3d_tasks_total = Counter('hunyuan3d_tasks_total', 'Total Hunyuan3D tasks', ['status'])
hunyuan3d_task_duration = Histogram('hunyuan3d_task_duration_seconds', 'Task duration')
```

### 5.3 告警规则

```yaml
# prometheus/alerts.yml
groups:
  - name: hunyuan3d
    rules:
      - alert: Hunyuan3DHighFailureRate
        expr: |
          rate(hunyuan3d_tasks_total{status="failed"}[5m])
          / rate(hunyuan3d_tasks_total[5m]) > 0.2
        for: 10m
        annotations:
          summary: "Hunyuan3D 任务失败率过高 (>20%)"
```

---

## 六、前端集成

### 6.1 API 调用

```typescript
// frontend/src/api/hunyuan3d.ts
import { apiClient } from './client'

export interface SubmitHunyuan3DRequest {
  Prompt?: string
  ImageUrl?: {
    Url: string  // 图片链接或 base64
  }
  Model?: '3.0' | '3.1'
  LowPoly?: boolean
  Sketch?: boolean
}

export interface SubmitHunyuan3DResponse {
  task_id: string
  job_id: string
  status: string
  message: string
}

export async function submitHunyuan3D(request: SubmitHunyuan3DRequest) {
  const response = await apiClient.post<SubmitHunyuan3DResponse>(
    '/api/v1/hunyuan3d/submit',
    request
  )
  return response.data
}
```

### 6.2 实时进度监听（SSE）

```typescript
// 复用现有 Task SSE 机制
const eventSource = new EventSource(
  `/api/v1/tasks/${task_id}/events?ticket=${sse_ticket}`
)

eventSource.addEventListener('progress', (event) => {
  const data = JSON.parse(event.data)
  console.log(`进度: ${data.progress}%`)
  // 更新 UI 进度条
})

eventSource.addEventListener('completed', (event) => {
  const data = JSON.parse(event.data)
  console.log(`完成！3D 模型 URL: ${data.result_uri}`)
  // 下载或预览 3D 模型
  eventSource.close()
})

eventSource.addEventListener('failed', (event) => {
  const data = JSON.parse(event.data)
  console.error(`失败: ${data.error_message}`)
  eventSource.close()
})
```

### 6.3 3D 模型预览

```typescript
// 使用 Three.js 预览 GLB 文件
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader'

function preview3DModel(url: string, container: HTMLElement) {
  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(75, container.clientWidth / container.clientHeight, 0.1, 1000)
  const renderer = new THREE.WebGLRenderer()
  
  renderer.setSize(container.clientWidth, container.clientHeight)
  container.appendChild(renderer.domElement)
  
  const loader = new GLTFLoader()
  loader.load(url, (gltf) => {
    scene.add(gltf.scene)
    camera.position.z = 5
    
    function animate() {
      requestAnimationFrame(animate)
      gltf.scene.rotation.y += 0.01
      renderer.render(scene, camera)
    }
    animate()
  })
}
```

---

## 七、常见问题

### Q1: API Key 无效或过期

**错误**:
```json
{
  "detail": "调用 Hunyuan3D API 失败: 401 Unauthorized"
}
```

**解决**:
1. 检查 `.env` 中的 `HUNYUAN3D_API_KEY` 是否正确
2. 在腾讯云控制台验证 API Key 状态
3. 必要时重新生成 API Key

### Q2: 任务一直停留在 pending 状态

**原因**: Worker 未启动或崩溃

**排查**:
```bash
# 检查 worker 进程
ps aux | grep hunyuan3d

# 查看 worker 日志
journalctl -u claywords-hunyuan3d-worker -n 50
```

**解决**: 重启 worker
```bash
sudo systemctl restart claywords-hunyuan3d-worker
```

### Q3: 下载 3D 文件失败

**错误**: `hunyuan3d_download_failed`

**原因**: 
- Hunyuan3D 返回的 URL 过期
- 网络连接问题

**解决**:
1. 增加 httpx 超时时间（当前 120s）
2. 添加重试机制
3. 检查服务器出网权限

### Q4: MinIO 存储未生效

**当前状态**: Worker 直接返回 Hunyuan3D 的原始 URL

**待补充**: 集成 MinIO 上传服务

```python
# app/services/hunyuan3d/worker.py:download_and_store_3d_file()
# TODO: 取消注释 MinIO 上传代码
from app.services.storage import get_storage_service
storage = get_storage_service()
minio_url = await storage.upload(...)
```

---

## 八、后续优化

### Phase 2（1 个月）

- [ ] 补充 MinIO 存储集成
- [ ] 添加 Prometheus metrics
- [ ] 用户配额限制（每日 N 次免费）
- [ ] 支持批量生成

### Phase 3（3 个月）

- [ ] 3D 模型编辑功能
- [ ] 与设计流程集成
- [ ] 多模态输入（文本 + 图片）
- [ ] 模型质量评分

---

## 九、验证清单

部署前检查：

- [ ] `.env` 已配置 `HUNYUAN3D_API_KEY`
- [ ] 测试脚本运行成功（`python scripts/test_hunyuan3d.py`）
- [ ] FastAPI 服务启动成功（访问 `/docs` 可见 `/api/v1/hunyuan3d/submit`）
- [ ] Worker 进程运行中（`ps aux | grep hunyuan3d`）
- [ ] 提交任务成功（返回 `task_id` 和 `job_id`）
- [ ] Worker 日志正常（出现 `polling_hunyuan3d_tasks`）
- [ ] 任务状态正常流转（pending → running → completed）
- [ ] 前端可通过 SSE 接收进度通知

---

## 十、联系与支持

- **文档**: [Hunyuan3D-integration-plan.md](Hunyuan3D-integration-plan.md)
- **腾讯云文档**: https://cloud.tencent.com/document/product/1804/126189
- **API 控制台**: https://console.cloud.tencent.com/tokenhub

---

**部署完成！** 🎉

运行测试脚本验证接口，然后启动服务开始使用。
