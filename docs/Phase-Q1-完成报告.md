# Phase Q1 完成报告

**日期**: 2026-06-21  
**状态**: ✅ 完成  
**耗时**: 约 2 小时

---

## 完成的任务

### Q1.1 Postgres 切换 ✅

#### Q1.1.1 升级 Docker Compose 配置 ✅
- [x] 升级 `infra/docker-compose.yml` 从 `pg13` 到 `pg16`
- [x] 添加 MinIO 服务配置
- [x] 验证：Docker 容器全部健康运行

#### Q1.1.2 修改配置默认使用 Postgres ✅
- [x] 修改 `backend/app/core/config.py` 默认 DATABASE_URL
- [x] 添加 `CRYPTO_PEPPER` 配置
- [x] 更新 `.env.example` 包含所有必要配置

#### Q1.1.3 实体层支持 Postgres 特性 ✅
- [x] 创建 `backend/app/models/types.py` 自定义类型
  - `Vector(1536)` - pgvector 兼容向量类型
  - `EncryptedStr` - 自动加密/解密字符串
  - `JSONB()` - Postgres JSONB 类型封装
- [x] 更新 `backend/app/models/entities.py`
  - 所有 JSON 列改为 JSONB
  - `DesignTemplate.embedding` 改为 `Vector(1536)`
  - `User` 添加 `email_encrypted` 和 `address_encrypted` 字段
  - 新增 3 张表：`StudioCraftOverride`, `IdempotencyKey`, `Task`
- [x] 验证：`\d design_templates` 显示 `vector(1536)` 类型

#### Q1.1.4 SQLite 数据导出脚本 ✅
- [x] 创建 `scripts/migrate_sqlite_to_pg.py`
  - 支持批量迁移
  - 保持外键依赖顺序
  - 包含数据验证功能
  - 错误回滚机制

### Q1.2 Alembic 版本化 ✅

#### Q1.2.1 初始化 Alembic 结构 ✅
- [x] 运行 `alembic init alembic`
- [x] 配置 `backend/alembic.ini` 完整配置
- [x] 修改 `backend/alembic/env.py` 支持异步迁移
  - 导入 `Base.metadata` 支持 autogenerate
  - 实现 `run_async_migrations()` 异步函数
  - 环境变量覆盖数据库 URL

#### Q1.2.2 Migration 001 - 初始 Schema ✅
- [x] 生成迁移文件 `c845aee3c751_001_initial_schema.py`
- [x] 创建 pgvector 扩展
- [x] 创建所有 13 张表（包含新增的 3 张表）
- [x] 创建所有索引和外键约束
- [x] 创建 ivfflat 索引：`idx_design_templates_embedding`
- [x] 实现 downgrade 函数
- [x] 验证：upgrade/downgrade 功能正常

#### Q1.2.3-5 新表迁移 ✅
所有新表已包含在 Migration 001 中：
- [x] `studio_craft_overrides` - 工作室工艺校准表
- [x] `idempotency_keys` - 幂等性键表
- [x] `tasks` - 任务持久化表

#### Q1.2.6 CI 中的迁移测试 ⏸️
- [ ] 创建 `.github/workflows/test.yml`
- **说明**: 暂缓，优先完成核心功能，后续 Phase Q9 统一处理 CI/CD

### Q1.3 加密字段统一 ✅

#### Q1.3.1 实现 EncryptedStr TypeDecorator ✅
- [x] 在 `backend/app/models/types.py` 实现 `EncryptedStr`
- [x] 自动加密/解密功能
- [x] 更新 User 模型使用 EncryptedStr
- [x] 验证：CRUD 测试中加密/解密正常工作

#### Q1.3.2 Pepper 轮换脚本 ✅
- [x] 创建 `scripts/rotate_pepper.py`
  - 支持双 pepper 共存模式
  - 批量处理用户数据
  - 包含确认和回滚机制
  - 7 天窗口期支持

---

## 验证结果

运行 `scripts/verify_q1.py` 全部通过：

```
=== Phase Q1 Verification ===

Testing database connection... [OK] Connected to PostgreSQL
  Version: PostgreSQL 16.13

Testing pgvector extension... [OK] pgvector 0.8.2 installed

Testing tables... [OK] All 13 tables created

Testing vector column type... [OK] embedding column is vector type

Testing ivfflat index... [OK] ivfflat index created

Testing encrypted fields... [OK] Encryption/decryption working

Testing CRUD operations... [OK] CRUD operations working

=== Summary ===
Passed: 7/7

[OK] All tests passed! Phase Q1 is complete.
```

---

## 数据库结构

### 核心表 (10 张)
1. `users` - 用户表（含加密字段）
2. `studios` - 工作室表
3. `sessions` - 会话表
4. `session_messages` - 会话消息表
5. `design_templates` - 设计模板表（含 vector embedding）
6. `designs` - 设计表
7. `design_versions` - 设计版本表
8. `orders` - 订单表
9. `order_logs` - 订单日志表

### 新增表 (3 张)
10. `studio_craft_overrides` - 工作室工艺校准表
11. `idempotency_keys` - 幂等性键表
12. `tasks` - 任务持久化表

### 系统表 (1 张)
13. `alembic_version` - Alembic 版本跟踪表

---

## 关键技术点

### 1. pgvector 集成
- **扩展版本**: 0.8.2
- **向量维度**: 1536 (与 text-embedding-3-small 兼容)
- **索引类型**: ivfflat (lists=100)
- **距离函数**: vector_cosine_ops

### 2. 自定义 SQLAlchemy 类型
- **Vector**: 跨数据库兼容，Postgres 用 pgvector，SQLite 用 JSON
- **EncryptedStr**: 透明加密/解密，使用 AES-256-GCM
- **JSONB**: Postgres 用 JSONB，其他数据库用 JSON

### 3. Alembic 异步支持
- 使用 `async_engine_from_config`
- `run_sync` 在异步上下文中运行同步迁移
- 完整的 upgrade/downgrade 支持

### 4. 数据安全
- 敏感字段使用 EncryptedStr 自动加密
- phone_hash 用于唯一性约束（不可逆）
- pepper 轮换机制支持

---

## 文件清单

### 修改的文件
- `infra/docker-compose.yml`
- `backend/app/core/config.py`
- `backend/app/models/entities.py`
- `backend/alembic.ini`
- `backend/alembic/env.py`
- `.env.example`

### 新增的文件
- `backend/app/models/types.py` - 自定义 SQLAlchemy 类型
- `backend/alembic/versions/c845aee3c751_001_initial_schema.py` - 初始迁移
- `scripts/migrate_sqlite_to_pg.py` - SQLite 迁移脚本
- `scripts/rotate_pepper.py` - Pepper 轮换脚本
- `scripts/verify_q1.py` - 验证脚本
- `infra/init.sql` - PostgreSQL 初始化脚本
- `.claude/plan.md` - Phase Q1 实施计划

---

## 使用说明

### 启动服务
```bash
# 启动 Docker 服务
cd infra
docker compose up -d

# 检查服务状态
docker ps
```

### 运行迁移
```bash
cd backend

# 查看当前版本
alembic current

# 升级到最新
alembic upgrade head

# 降级
alembic downgrade -1

# 回到初始状态
alembic downgrade base
```

### SQLite 数据迁移
```bash
python scripts/migrate_sqlite_to_pg.py \
  --source test.db \
  --target postgresql://claywords:claywords_secret@localhost:5432/claywords \
  --verify
```

### Pepper 轮换
```bash
# 第一步：开启双 pepper 模式
python scripts/rotate_pepper.py \
  --old-pepper "old_value" \
  --new-pepper "new_value" \
  --dual-mode

# 第二步：7 天后完成轮换
python scripts/rotate_pepper.py \
  --old-pepper "old_value" \
  --new-pepper "new_value" \
  --finalize
```

---

## 后续接口

Phase Q1 完成后，为后续阶段准备好的接口：

### 为 Q2 准备（Redis Streams）
- `tasks` 表已就绪，可与 Redis 双写
- `idempotency_keys` 表支持幂等性中间件

### 为 Q3 准备（3D 模型）
- `design_templates.embedding` 向量检索已可用
- ivfflat 索引已创建，可直接导入 30 个模板
- Vector 类型自动处理编码/解码

---

## 已知问题与限制

### 1. CI/CD 管道
- 暂未实现自动化测试管道
- 计划在 Phase Q9 统一处理

### 2. 迁移脚本测试
- `migrate_sqlite_to_pg.py` 已实现但未在真实数据上测试
- 需要在有 SQLite 数据时验证

### 3. 性能优化
- ivfflat 索引参数 (lists=100) 基于小数据集
- 生产环境需根据实际模板数量调整

---

## 总结

Phase Q1 成功完成了数据层从 SQLite 演示环境到 PostgreSQL + pgvector 生产环境的迁移。核心成果包括：

✅ **完整的数据库迁移系统** - Alembic + 异步支持  
✅ **pgvector 向量检索** - 为 AI 模型 embedding 做好准备  
✅ **数据加密机制** - EncryptedStr 自动加密敏感字段  
✅ **新增 3 张业务表** - 支持后续功能开发  
✅ **完整的验证脚本** - 7/7 测试全部通过  

**下一步**: 进入 Phase Q2 - 队列与 SSE 落到 Redis Streams
