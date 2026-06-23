# 腾讯云混元 3D (Hunyuan3D) 接入方案

## 一、API 基本信息

### 1.1 接口地址

- **提交任务**: `https://api.ai3d.cloud.tencent.com/v1/ai3d/submit`
- **查询结果**: `https://api.ai3d.cloud.tencent.com/v1/ai3d/query`
- **base_url**: `https://api.ai3d.cloud.tencent.com`

### 1.2 鉴权方式

```http
Authorization: sk-YOUR_API_KEY
Content-Type: application/json
```

**注意**: 不是 `Bearer sk-xxx`，直接放 API Key。

### 1.3 模型版本

- **3.0**: 支持全部参数（LowPoly, Sketch 等）
- **3.1**: 最新版本，不支持 LowPoly / Sketch，默认使用 3.0

### 1.4 输入方式

1. **文本 Prompt**: `{"Prompt": "小狗"}`
2. **图片 URL**: `{"ImageUrl": {"Url": "https://..."}}`
3. **图片 base64**: `{"ImageUrl": {"Url": "data:image/jpeg;base64,xxx"}}`

### 1.5 工作流程

```
用户提交 → submit 接口 → 返回 JobId
             ↓
         轮询 query 接口 → 返回状态 + 3D 文件 URL
             ↓
         下载 3D 文件 → 存储到 MinIO/S3
```

---

## 二、架构设计

### 2.1 整体流程

```
┌─────────────┐
│   用户请求   │  POST /api/v1/hunyuan3d/submit
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  ClayWords Backend                      │
│  - 调用 Hunyuan3D submit 接口           │
│  - 创建 Task 记录 (task_id, job_id)     │
│  - 返回 task_id 给前端                  │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  ARQ 后台 Worker                        │
│  - 定时轮询未完成的 3D 任务              │
│  - 调用 Hunyuan3D query 接口            │
│  - 任务完成 → 下载 3D 文件到 MinIO       │
│  - 更新 Task 状态                       │
│  - 通过 SSE 推送进度给前端               │
└─────────────────────────────────────────┘
```

### 2.2 目录结构

```
backend/
├── app/
│   ├── api/
│   │   └── hunyuan3d.py          # REST 端点
│   ├── services/
│   │   └── hunyuan3d/
│   │       ├── __init__.py
│   │       ├── client.py         # Hunyuan3D API 客户端
│   │       ├── schemas.py        # 请求/响应数据结构
│   │       └── worker.py         # ARQ 后台轮询任务
│   └── core/
│       └── config.py             # 新增 HUNYUAN3D_API_KEY
├── alembic/versions/
│   └── xxxx_add_hunyuan3d_fields.py  # Migration（可选）
└── scripts/
    └── test_hunyuan3d.py         # 接口测试脚本
```

---

## 三、数据模型设计

### 3.1 复用现有 Task 表

```python
# app/models/entities.py (已存在)
class Task(Base):
    task_id: str                    # 主键
    state: str                      # pending/running/completed/failed
    payload: dict                   # 存储 {"job_id": "xxx", "prompt": "...", "image_url": "..."}
    result_uri: Optional[str]       # 3D 文件下载地址（MinIO URL）
    progress: int                   # 0-100
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
```

**payload 字段示例**:
```json
{
  "task_type": "hunyuan3d",
  "job_id": "1387416933258346496",
  "prompt": "一只可爱的小狗",
  "image_url": null,
  "model": "3.0"
}
```

### 3.2 可选：新增专用表

若需要更丰富的 3D 任务元数据（如纹理质量、多边形数量），可新增：

```python
class Hunyuan3DTask(Base):
    __tablename__ = "hunyuan3d_tasks"
    
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.task_id"), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    model: Mapped[str] = mapped_column(String(10), default="3.0")
    low_poly: Mapped[bool] = mapped_column(Boolean, default=False)
    sketch: Mapped[bool] = mapped_column(Boolean, default=False)
    result_glb_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    polygon_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
```

**推荐**: 先复用 Task 表，后续需要再扩展。

---

## 四、代码实现

### 4.1 配置管理

```python
# app/core/config.py
class Settings(BaseSettings):
    # ... 现有配置
    
    # Hunyuan3D 配置
    HUNYUAN3D_API_KEY: str = Field(default="", env="HUNYUAN3D_API_KEY")
    HUNYUAN3D_BASE_URL: str = "https://api.ai3d.cloud.tencent.com"
    HUNYUAN3D_POLL_INTERVAL: int = 5  # 轮询间隔（秒）
    HUNYUAN3D_MAX_POLL_ATTEMPTS: int = 120  # 最大轮询次数（120 * 5s = 10min）

settings = Settings()
```

**环境变量**:
```bash
# .env
HUNYUAN3D_API_KEY=sk-YOUR_ACTUAL_KEY_HERE
```

### 4.2 数据模型

```python
# app/services/hunyuan3d/schemas.py
from pydantic import BaseModel, Field
from typing import Optional

class ImageUrl(BaseModel):
    """图片 URL 或 base64"""
    Url: str = Field(..., description="图片链接或 base64 (data:image/jpeg;base64,xxx)")

class SubmitRequest(BaseModel):
    """提交 3D 生成任务请求"""
    Prompt: Optional[str] = Field(None, description="文本描述")
    ImageUrl: Optional[ImageUrl] = Field(None, description="图片输入")
    Model: str = Field("3.0", description="模型版本 3.0 或 3.1")
    LowPoly: Optional[bool] = Field(None, description="是否低多边形（仅 3.0 支持）")
    Sketch: Optional[bool] = Field(None, description="是否草图风格（仅 3.0 支持）")

class SubmitResponse(BaseModel):
    """提交任务响应"""
    JobId: str

class QueryRequest(BaseModel):
    """查询任务状态请求"""
    JobId: str

class QueryResponse(BaseModel):
    """查询任务状态响应"""
    Status: str  # pending/running/completed/failed
    Progress: Optional[int] = None  # 0-100
    ResultUrl: Optional[str] = None  # 3D 文件下载地址
    ErrorMessage: Optional[str] = None
```

### 4.3 Hunyuan3D 客户端

```python
# app/services/hunyuan3d/client.py
import httpx
from app.core.config import settings
from app.services.hunyuan3d.schemas import (
    SubmitRequest, SubmitResponse,
    QueryRequest, QueryResponse
)
import structlog

logger = structlog.get_logger()

class Hunyuan3DClient:
    """腾讯云混元 3D API 客户端"""
    
    def __init__(self):
        self.base_url = settings.HUNYUAN3D_BASE_URL
        self.api_key = settings.HUNYUAN3D_API_KEY
        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }
    
    async def submit(self, request: SubmitRequest) -> SubmitResponse:
        """
        提交 3D 生成任务
        
        Returns:
            SubmitResponse: 包含 JobId
        
        Raises:
            httpx.HTTPStatusError: API 请求失败
        """
        url = f"{self.base_url}/v1/ai3d/submit"
        
        # 过滤 None 值（Model 3.1 不支持 LowPoly/Sketch）
        payload = request.model_dump(exclude_none=True)
        
        logger.info("hunyuan3d_submit", payload=payload)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            logger.info("hunyuan3d_submit_success", job_id=data.get("JobId"))
            
            return SubmitResponse(**data)
    
    async def query(self, job_id: str) -> QueryResponse:
        """
        查询任务状态
        
        Returns:
            QueryResponse: 包含状态和结果 URL
        """
        url = f"{self.base_url}/v1/ai3d/query"
        payload = {"JobId": job_id}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            logger.debug("hunyuan3d_query", job_id=job_id, status=data.get("Status"))
            
            return QueryResponse(**data)

# 全局实例
hunyuan3d_client = Hunyuan3DClient()
```

### 4.4 REST 端点

```python
# app/api/hunyuan3d.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_session
from app.core.auth import get_current_user, UserInfo
from app.services.hunyuan3d.client import hunyuan3d_client
from app.services.hunyuan3d.schemas import SubmitRequest
from app.models.entities import Task
from app.services.tasks.task_service import TaskService, get_task_service
import uuid
from datetime import datetime, timezone

router = APIRouter(prefix="/hunyuan3d", tags=["Hunyuan3D"])

@router.post("/submit")
async def submit_3d_generation(
    request: SubmitRequest,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    task_service: TaskService = Depends(get_task_service)
):
    """
    提交 3D 生成任务
    
    - 支持文本 Prompt 或图片输入
    - 返回 task_id，前端可通过 /tasks/{task_id} 查询状态
    """
    # 校验输入
    if not request.Prompt and not request.ImageUrl:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prompt 或 ImageUrl 至少提供一个"
        )
    
    # 调用 Hunyuan3D submit 接口
    try:
        submit_response = await hunyuan3d_client.submit(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"调用 Hunyuan3D API 失败: {str(e)}"
        )
    
    # 创建 Task 记录
    task_id = str(uuid.uuid4())
    payload = {
        "task_type": "hunyuan3d",
        "job_id": submit_response.JobId,
        "prompt": request.Prompt,
        "image_url": request.ImageUrl.Url if request.ImageUrl else None,
        "model": request.Model,
        "user_id": current_user.user_id
    }
    
    task_info = await task_service.create_task(
        task_id=task_id,
        state="pending",
        payload=payload
    )
    
    return {
        "task_id": task_id,
        "job_id": submit_response.JobId,
        "status": "pending",
        "message": "3D 生成任务已提交，请通过 task_id 查询进度"
    }
```

### 4.5 ARQ 后台轮询

```python
# app/services/hunyuan3d/worker.py
from arq import cron
from sqlalchemy import select, update
from app.models.entities import Task
from app.core.db import async_session_maker
from app.services.hunyuan3d.client import hunyuan3d_client
from app.core.config import settings
import httpx
import structlog

logger = structlog.get_logger()

async def poll_hunyuan3d_tasks(ctx):
    """
    定时轮询 Hunyuan3D 任务状态
    
    执行频率: 每 5 秒一次（由 arq cron 配置）
    """
    async with async_session_maker() as session:
        # 查询所有 pending/running 的 Hunyuan3D 任务
        stmt = select(Task).where(
            Task.state.in_(["pending", "running"]),
            Task.payload["task_type"].astext == "hunyuan3d"
        )
        result = await session.execute(stmt)
        tasks = result.scalars().all()
        
        for task in tasks:
            job_id = task.payload.get("job_id")
            if not job_id:
                continue
            
            try:
                # 查询任务状态
                query_response = await hunyuan3d_client.query(job_id)
                
                # 更新任务进度
                if query_response.Status == "running":
                    task.state = "running"
                    task.progress = query_response.Progress or 0
                
                elif query_response.Status == "completed":
                    # 下载 3D 文件到 MinIO
                    if query_response.ResultUrl:
                        result_uri = await download_and_store_3d_file(
                            query_response.ResultUrl,
                            task.task_id
                        )
                        task.result_uri = result_uri
                    
                    task.state = "completed"
                    task.progress = 100
                    logger.info("hunyuan3d_task_completed", task_id=task.task_id, job_id=job_id)
                
                elif query_response.Status == "failed":
                    task.state = "failed"
                    task.error_message = query_response.ErrorMessage or "任务失败"
                    logger.error("hunyuan3d_task_failed", task_id=task.task_id, error=task.error_message)
                
                await session.commit()
                
                # 通过 SSE 推送进度（可选）
                # await broadcast_task_progress(task.task_id, task.state, task.progress)
                
            except Exception as e:
                logger.error("poll_hunyuan3d_error", task_id=task.task_id, error=str(e))
                continue

async def download_and_store_3d_file(result_url: str, task_id: str) -> str:
    """
    下载 3D 文件并存储到 MinIO
    
    Returns:
        str: MinIO 中的文件 URL
    """
    from app.services.storage import get_storage_service
    
    # 下载文件
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(result_url)
        response.raise_for_status()
        file_data = response.content
    
    # 上传到 MinIO
    storage = get_storage_service()
    file_key = f"hunyuan3d/{task_id}.glb"  # 假设是 GLB 格式
    
    minio_url = await storage.upload(
        bucket="claywords-3d-models",
        key=file_key,
        data=file_data,
        content_type="model/gltf-binary"
    )
    
    logger.info("3d_file_stored", task_id=task_id, url=minio_url)
    return minio_url

# ARQ Worker 配置
class WorkerSettings:
    functions = [poll_hunyuan3d_tasks]
    cron_jobs = [
        cron(poll_hunyuan3d_tasks, second={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55})
        # 每 5 秒执行一次
    ]
```

### 4.6 集成到主应用

```python
# app/main.py
from app.api import hunyuan3d

app.include_router(hunyuan3d.router, prefix="/api/v1")
```

---

## 五、测试脚本

```python
# scripts/test_hunyuan3d.py
"""
测试 Hunyuan3D API 接口
"""
import asyncio
import sys
sys.path.insert(0, "./backend")

from app.services.hunyuan3d.client import hunyuan3d_client
from app.services.hunyuan3d.schemas import SubmitRequest

async def test_text_to_3d():
    """测试文本生成 3D"""
    request = SubmitRequest(Prompt="一只可爱的小狗", Model="3.0")
    
    # 提交任务
    submit_response = await hunyuan3d_client.submit(request)
    print(f"✓ 任务已提交，JobId: {submit_response.JobId}")
    
    # 轮询结果
    job_id = submit_response.JobId
    max_attempts = 120
    
    for i in range(max_attempts):
        await asyncio.sleep(5)
        
        query_response = await hunyuan3d_client.query(job_id)
        print(f"[{i+1}/{max_attempts}] 状态: {query_response.Status}, 进度: {query_response.Progress}%")
        
        if query_response.Status == "completed":
            print(f"✓ 生成完成！结果 URL: {query_response.ResultUrl}")
            return query_response.ResultUrl
        
        elif query_response.Status == "failed":
            print(f"✗ 任务失败: {query_response.ErrorMessage}")
            return None
    
    print("✗ 超时：10 分钟后任务仍未完成")
    return None

if __name__ == "__main__":
    asyncio.run(test_text_to_3d())
```

---

## 六、部署与配置

### 6.1 环境变量

```bash
# .env
HUNYUAN3D_API_KEY=sk-YOUR_ACTUAL_KEY_HERE
HUNYUAN3D_BASE_URL=https://api.ai3d.cloud.tencent.com
HUNYUAN3D_POLL_INTERVAL=5
HUNYUAN3D_MAX_POLL_ATTEMPTS=120
```

### 6.2 ARQ Worker 启动

```bash
# 启动 ARQ worker（后台轮询）
cd backend
arq app.services.hunyuan3d.worker.WorkerSettings
```

### 6.3 依赖安装

```bash
# requirements.txt 新增
httpx>=0.27.0  # 已有
arq>=0.26.0    # 已有
```

---

## 七、前端集成

### 7.1 提交任务

```typescript
// frontend/src/api/hunyuan3d.ts
export interface SubmitRequest {
  Prompt?: string
  ImageUrl?: {
    Url: string  // 图片链接或 base64
  }
  Model?: '3.0' | '3.1'
}

export async function submitHunyuan3D(request: SubmitRequest) {
  const response = await apiClient.post('/api/v1/hunyuan3d/submit', request)
  return response.data  // { task_id, job_id, status }
}
```

### 7.2 查询进度（SSE）

```typescript
// 复用现有 Task SSE 机制
const eventSource = new EventSource(`/api/v1/tasks/${task_id}/events`)

eventSource.addEventListener('progress', (event) => {
  const data = JSON.parse(event.data)
  console.log(`进度: ${data.progress}%`)
})

eventSource.addEventListener('completed', (event) => {
  const data = JSON.parse(event.data)
  console.log(`完成！3D 模型 URL: ${data.result_uri}`)
  // 下载或预览 3D 模型
})
```

---

## 八、安全与最佳实践

### 8.1 API Key 保护

- ✅ **存储**: 使用环境变量，不提交到代码仓库
- ✅ **轮换**: 定期在腾讯云控制台轮换 API Key
- ✅ **权限**: 仅后端服务持有 Key，前端不可见

### 8.2 错误处理

```python
# 捕获 API 异常
try:
    submit_response = await hunyuan3d_client.submit(request)
except httpx.HTTPStatusError as e:
    if e.response.status_code == 401:
        logger.error("hunyuan3d_auth_error", detail="API Key 无效或过期")
    elif e.response.status_code == 429:
        logger.warning("hunyuan3d_rate_limit", detail="触发限流，稍后重试")
    else:
        logger.error("hunyuan3d_api_error", status=e.response.status_code, body=e.response.text)
    raise HTTPException(status_code=502, detail="调用 Hunyuan3D API 失败")
```

### 8.3 超时与重试

```python
# 轮询超时保护
if task.created_at < datetime.now(timezone.utc) - timedelta(minutes=15):
    task.state = "failed"
    task.error_message = "任务超时（15 分钟）"
    await session.commit()
```

### 8.4 限流保护

```python
# 用户每小时最多提交 10 个 3D 生成任务
from app.core.rate_limiter import check_rate_limit

@router.post("/submit")
async def submit_3d_generation(...):
    if not await check_rate_limit(f"hunyuan3d:{current_user.user_id}", max_requests=10, window=3600):
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")
    # ...
```

---

## 九、成本估算

**腾讯云混元 3D 定价** (2026 年 6 月):
- 混元生 3D（专业版）: ¥1.5 / 次（文档未提及，需查看控制台实际价格）

**预估成本**:
- 每天 100 次生成 × ¥1.5 = ¥150 / 天
- 每月 3000 次生成 × ¥1.5 = ¥4500 / 月

**优化建议**:
- 缓存常见模型（如「小狗」、「茶杯」）
- 限制用户免费生成次数（如每日 3 次）

---

## 十、后续优化

### Phase 1（当前方案）
- ✅ 基础接入（文本/图片 → 3D）
- ✅ 异步任务管理
- ✅ 后台轮询 + 文件存储

### Phase 2（1 个月后）
- 支持 Model 3.1（去掉 LowPoly/Sketch 参数）
- 3D 模型预览（前端集成 Three.js）
- 用户 3D 模型库管理

### Phase 3（3 个月后）
- 多模态输入（文本 + 参考图 → 3D）
- 3D 编辑功能（调整纹理、材质）
- 与设计流程集成（设计 → 3D → 订单）

---

## 十一、风险与回退

### 11.1 风险点

1. **API 稳定性**: 腾讯云服务可用性未知
   - 缓解: 添加超时和重试机制，记录失败率

2. **成本超支**: 用户滥用 API
   - 缓解: 限流 + 每日配额

3. **生成质量**: 3D 模型不符合预期
   - 缓解: 提供 Prompt 优化建议，支持重新生成

### 11.2 回退方案

```python
# app/core/config.py
ENABLE_HUNYUAN3D: bool = Field(default=True, env="ENABLE_HUNYUAN3D")

# app/api/hunyuan3d.py
if not settings.ENABLE_HUNYUAN3D:
    raise HTTPException(503, detail="3D 生成服务暂时不可用")
```

---

## 十二、验证清单

### 本地测试

```bash
# 1. 配置环境变量
export HUNYUAN3D_API_KEY=sk-YOUR_KEY

# 2. 运行测试脚本
python scripts/test_hunyuan3d.py

# 预期输出:
# ✓ 任务已提交，JobId: 1387416933258346496
# [1/120] 状态: running, 进度: 10%
# [2/120] 状态: running, 进度: 50%
# [3/120] 状态: completed, 进度: 100%
# ✓ 生成完成！结果 URL: https://...

# 3. 启动后端 + ARQ worker
uvicorn app.main:app --reload &
arq app.services.hunyuan3d.worker.WorkerSettings &

# 4. 调用 API
curl -X POST http://localhost:8000/api/v1/hunyuan3d/submit \
  -H "Authorization: Bearer YOUR_USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"Prompt": "一只可爱的小狗", "Model": "3.0"}'

# 5. 查询任务状态
curl http://localhost:8000/api/v1/tasks/{task_id}
```

### 生产部署

- ✅ API Key 已配置到生产环境变量
- ✅ ARQ Worker 已启动（systemd / Docker）
- ✅ MinIO bucket `claywords-3d-models` 已创建
- ✅ 限流规则已配置
- ✅ 监控告警已设置（任务失败率 > 10%）

---

## 总结

**当前方案特点**:
- ✅ 兼容 OpenAI 规范，接入简单
- ✅ 异步任务管理，前端实时通知
- ✅ 复用现有基础设施（Task 表、ARQ、MinIO、SSE）
- ✅ 支持文本和图片两种输入方式
- ✅ 完整的错误处理和回退机制

**预期开发时间**:
- Day 1: 配置 + client.py + schemas.py（2h）
- Day 2: REST 端点 + worker.py（4h）
- Day 3: 测试 + 调试（2h）
- **总计**: 1-2 天完成基础接入

**后续行动**:
1. 在腾讯云控制台创建 API Key（如果还没有）
2. 运行 `scripts/test_hunyuan3d.py` 验证接口可用性
3. 实现 `client.py` → `worker.py` → `REST 端点`
4. 前端集成（提交表单 + 3D 模型预览）
