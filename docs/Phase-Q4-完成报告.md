# Phase Q4 完成报告

**日期**: 2026-06-21  
**状态**: ✅ 核心功能已实现  
**说明**: MinIO 包需要安装后才能完整测试

---

## 完成的任务

### Q4.1 MinIO 预签名上传 ✅

#### Q4.1.1 MinIO 客户端和预签名 URL ✅
- [x] 创建 `backend/app/core/storage.py` - MinIOClient 完整实现
- [x] 支持预签名 PUT URL（1小时有效期）
- [x] 支持预签名 GET URL（24小时有效期）
- [x] 自动初始化 bucket（如不存在则创建）
- [x] 对象键生成（带 UUID 防冲突）

#### Q4.1.2 上传记录表和状态机 ✅
- [x] 新增 `Upload` 模型到 `entities.py`
- [x] 字段：upload_id, object_key, file_name, file_size, mime_type, state, scan_result, uploader_id
- [x] 状态机：pending → scanning → clean/quarantined
- [x] 索引：state, uploader_id, created_at
- [x] 迁移文件：`002_add_uploads_table.py` 已生成并应用

#### Q4.1.3 上传 API ✅
- [x] 创建 `backend/app/api/uploads.py` - 完整上传 API
- [x] `POST /uploads/init` - 初始化上传，返回预签名 URL
- [x] `GET /uploads/{id}` - 查询上传状态
- [x] `POST /uploads/{id}/confirm` - 确认上传完成（触发扫描）
- [x] `GET /uploads` - 列出用户的上传记录

### Q4.2 文件类型和大小限制 ✅

#### Q4.2.1 MIME 类型白名单 ✅
- [x] 图片：image/jpeg, image/png, image/webp
- [x] 3D 模型：model/gltf-binary, application/octet-stream
- [x] 文档：application/pdf
- [x] 服务端验证（init 时检查）

#### Q4.2.2 文件大小限制 ✅
- [x] 图片：10MB
- [x] 3D 模型：50MB
- [x] 文档：5MB
- [x] 返回 413 Payload Too Large

### Q4.3 安全扫描占位符 ✅

#### Q4.3.1 状态机实现 ✅
- [x] pending - 预签名 URL 已生成，等待上传
- [x] scanning - （Phase Q5 实现）扫描中
- [x] clean - 扫描通过，可公开访问
- [x] quarantined - （Phase Q5 实现）发现威胁，隔离

#### Q4.3.2 自动标记为 clean ✅
- [x] `POST /uploads/{id}/confirm` 当前自动标记为 clean
- [x] scan_result 包含占位说明：Phase Q4 auto-approved
- [x] Phase Q5 将集成真实 ClamAV 扫描

---

## 文件清单

### 新增的文件
- `backend/app/core/storage.py` - MinIO 客户端
- `backend/app/api/uploads.py` - 上传 API
- `backend/alembic/versions/86ad82ebb698_002_add_uploads_table.py` - 迁移文件
- `scripts/verify_q4.py` - 验证脚本

### 修改的文件
- `backend/app/models/entities.py` - 新增 Upload 模型
- `backend/app/main.py` - 注册上传 API，初始化 MinIO
- `backend/requirements.txt` - 添加 minio>=7.2.0

---

## API 使用示例

### 1. 初始化上传

```bash
POST /api/v1/uploads/init
Authorization: Bearer <token>
Content-Type: application/json

{
  "file_name": "avatar.jpg",
  "file_size": 2048576,
  "mime_type": "image/jpeg",
  "upload_type": "avatar"
}
```

**响应**:
```json
{
  "upload_id": "uuid",
  "object_key": "avatars/abc123.jpg",
  "presigned_url": "http://localhost:9000/claywords/avatars/abc123.jpg?...",
  "expires_in": 3600
}
```

### 2. 客户端直接上传到 MinIO

```bash
PUT <presigned_url>
Content-Type: image/jpeg

<binary data>
```

### 3. 确认上传完成

```bash
POST /api/v1/uploads/{upload_id}/confirm
Authorization: Bearer <token>
```

**响应**:
```json
{
  "status": "ok",
  "state": "clean"
}
```

### 4. 查询上传状态

```bash
GET /api/v1/uploads/{upload_id}
Authorization: Bearer <token>
```

**响应**:
```json
{
  "upload_id": "uuid",
  "state": "clean",
  "scan_result": {
    "scanned": false,
    "clean": true,
    "note": "Phase Q4: Auto-approved, real scan in Q5"
  },
  "public_url": "http://localhost:9000/claywords/avatars/abc123.jpg"
}
```

---

## 数据库结构

### uploads 表

| 字段 | 类型 | 说明 |
|------|------|------|
| upload_id | VARCHAR(36) | 主键 |
| object_key | VARCHAR(500) | MinIO 对象键（唯一） |
| file_name | VARCHAR(255) | 原始文件名 |
| file_size | INTEGER | 文件大小（字节）|
| mime_type | VARCHAR(100) | MIME 类型 |
| state | VARCHAR(20) | 状态：pending/scanning/clean/quarantined |
| scan_result | JSONB | 扫描结果 JSON |
| uploader_id | VARCHAR(36) | 上传者 user_id |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

**索引**:
- idx_uploads_state (state)
- idx_uploads_uploader (uploader_id)
- idx_uploads_created (created_at)

---

## 安全特性

### 已实现
✅ **MIME 类型白名单** - 服务端验证，拒绝未授权类型  
✅ **文件大小限制** - 防止超大文件占用存储  
✅ **预签名 URL** - 客户端直传，减轻服务器负载  
✅ **一次性 URL** - 1小时有效期，过期自动失效  
✅ **状态追踪** - 每个上传都有明确状态  
✅ **用户隔离** - 只能查询自己的上传记录  

### Phase Q5 待实现
⏸️ **ClamAV 病毒扫描** - 上传后自动扫描  
⏸️ **隔离机制** - 发现威胁后阻止访问  
⏸️ **扫描队列** - 异步扫描不阻塞上传  

---

## 集成要求

### Docker Compose
MinIO 服务已在 `infra/docker-compose.yml` 中配置：
```yaml
minio:
  image: minio/minio
  ports:
    - "9000:9000"
    - "9001:9001"
  environment:
    MINIO_ROOT_USER: claywords
    MINIO_ROOT_PASSWORD: claywords_secret
  command: server /data --console-address ":9001"
```

### 环境变量
```bash
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=claywords
MINIO_SECRET_KEY=claywords_secret
MINIO_BUCKET=claywords
MINIO_SECURE=false
```

### 安装依赖
```bash
cd backend
pip install -r requirements.txt  # 包含 minio>=7.2.0
```

---

## 测试计划

### 单元测试（需要 MinIO 运行）
```bash
# 启动 MinIO
docker compose -f infra/docker-compose.yml up -d minio

# 安装依赖
pip install minio>=7.2.0

# 运行验证
python scripts/verify_q4.py
```

### 集成测试
1. 初始化上传 → 获取预签名 URL
2. 使用 curl 上传文件到预签名 URL
3. 确认上传完成 → 状态变为 clean
4. 获取 public_url → 能够访问文件

---

## 与其他 Phase 的接口

### 为 Phase Q5 准备（病毒扫描）
- Upload 表的 state 字段支持完整状态机
- scan_result JSONB 字段可存储 ClamAV 结果
- confirm API 可触发扫描任务入队

### 为 Phase Q6 准备（订单工单）
- 上传的文件可关联到订单
- public_url 可嵌入工单 PDF
- 支持用户头像、设计稿、参考图等多种类型

---

## 后续工作

### Phase Q5 需要实现
- [ ] ClamAV 容器化部署
- [ ] 扫描任务队列（Redis Streams）
- [ ] 扫描 Worker（调用 ClamAV REST API）
- [ ] 隔离文件移动到 quarantine/ 前缀
- [ ] 扫描失败重试机制

### Phase Q6 可直接使用
- [x] 上传 API 已就绪
- [x] 状态查询已就绪
- [x] public_url 生成已就绪

---

## 总结

Phase Q4 成功实现了文件上传的核心基础设施：

✅ **MinIO 集成** - 对象存储客户端和预签名 URL  
✅ **上传 API** - 完整的初始化、确认、查询流程  
✅ **安全验证** - MIME 类型和文件大小限制  
✅ **状态机** - pending → clean 流程（Phase Q5 补充 scanning）  
✅ **数据持久化** - uploads 表和迁移  

**下一步**: 
- Phase Q5 - 集成 ClamAV 病毒扫描
- 或跳过 Q5，继续 Phase Q6 - 支付与物流

**说明**: 完整测试需要先安装 minio 包和启动 MinIO 服务。
