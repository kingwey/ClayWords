# Phase Q1 实施计划：数据层迁移到生产级

## 概述
将 ClayWords 项目的数据层从 SQLite 演示库迁移到 PostgreSQL 16 + pgvector 生产环境，并建立 Alembic 版本化迁移系统。

## 当前状态分析

### 已有基础
- ✅ SQLAlchemy 2.0 async 架构已就绪
- ✅ requirements.txt 已包含 `alembic>=1.13.0` 和 `asyncpg>=0.29.0`
- ✅ docker-compose.yml 已配置 Postgres（但版本为 pg13，需升级）
- ✅ 完整的实体模型定义（10个表）
- ✅ 基础的加密服务（CryptoService）
- ✅ 空的 alembic.ini 文件

### 现有问题
- ❌ 默认使用 SQLite (`sqlite+aiosqlite:///./test.db`)
- ❌ Docker 使用 `pgvector/pgvector:pg13`，需升级到 pg16
- ❌ 实体模型使用 `JSON` 而非 `JSONB`
- ❌ 没有 `vector(1536)` 类型支持
- ❌ Alembic 目录结构未初始化
- ❌ 没有迁移文件
- ❌ 加密字段未统一为 TypeDecorator
- ❌ 缺少新表：`studio_craft_overrides`, `idempotency_keys`, `tasks`

## 实施步骤

### Q1.1 Postgres 切换

#### Q1.1.1 升级 Docker Compose 配置
**文件**: `infra/docker-compose.yml`

**修改点**:
1. 升级镜像从 `pgvector/pgvector:pg13` → `pgvector/pgvector:pg16`
2. 添加 MinIO 服务配置（当前缺失）
3. 更新 `.env.example` 添加敏感配置项

**验收**: 
```bash
docker compose -f infra/docker-compose.yml up -d postgres
docker exec -it claywords_postgres psql -U claywords -c '\dx'
# 应显示 vector 扩展
```

#### Q1.1.2 修改配置默认使用 Postgres
**文件**: `backend/app/core/config.py`

**修改点**:
1. `DATABASE_URL` 默认值改为 `postgresql+asyncpg://claywords:claywords_secret@localhost:5432/claywords`
2. 添加环境变量 fallback 逻辑
3. 添加 MinIO 相关配置（USER/PASSWORD）

**验收**: 
- 启动应用连接到 Postgres 成功
- SQLite 仍可作为测试 fallback

#### Q1.1.3 实体层支持 Postgres 特性
**文件**: `backend/app/models/entities.py`

**修改点**:
1. 创建 `Vector` 自定义类型（SQLAlchemy TypeDecorator）
2. `DesignTemplate.embedding` 改为 `Vector(1536)`
3. 所有 `SQLAlchemyJSON` 改为 `JSONB`（仅 Postgres 生效）
4. 添加条件导入：SQLite 时回退到 JSON

**新文件**: `backend/app/models/types.py`
```python
from sqlalchemy import TypeDecorator, Text
from sqlalchemy.dialects.postgresql import ARRAY
import json

class Vector(TypeDecorator):
    """pgvector compatible type"""
    impl = Text
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            from pgvector.sqlalchemy import Vector as PGVector
            return PGVector(self.dimension)
        return Text()
```

**验收**:
```sql
\d design_templates
-- embedding 列应显示为 vector(1536)
```

#### Q1.1.4 SQLite 数据导出脚本
**新文件**: `scripts/migrate_sqlite_to_pg.py`

**功能**:
1. 连接 SQLite 读取所有表数据
2. 批量插入到 Postgres，保持 ID 一致
3. 处理外键依赖顺序
4. 验证记录数一致性
5. 错误回滚机制

**验收**:
```bash
python scripts/migrate_sqlite_to_pg.py --source test.db --target postgresql://...
# 检查迁移后数据数量
```

### Q1.2 Alembic 版本化

#### Q1.2.1 初始化 Alembic 结构
**命令**:
```bash
cd backend
alembic init alembic
```

**配置文件修改**:
1. `backend/alembic.ini`: 设置 `sqlalchemy.url` 读取环境变量
2. `backend/alembic/env.py`: 导入 `Base.metadata`，支持 autogenerate

**验收**:
```bash
alembic current  # 应返回空（尚无迁移）
alembic revision --autogenerate -m "initial"  # 应生成迁移文件
```

#### Q1.2.2 Migration 001 - 初始 Schema
**文件**: `backend/alembic/versions/001_initial_schema.py`

**内容**:
1. 创建 pgvector 扩展
2. 创建所有现有表（users, studios, sessions, session_messages, design_templates, designs, design_versions, orders, order_logs）
3. 创建索引：
   - `users.phone_hash` UNIQUE
   - `orders.idempotency_key` UNIQUE
   - `design_templates.embedding` ivfflat 索引
4. 创建外键约束

**验收**:
```bash
alembic upgrade head  # 应用迁移
alembic downgrade base  # 回滚成功
alembic upgrade head  # 再次应用
```

#### Q1.2.3 Migration 002 - studio_craft_overrides 表
**文件**: `backend/alembic/versions/002_studio_craft_overrides.py`

**表结构**:
```sql
CREATE TABLE studio_craft_overrides (
    id UUID PRIMARY KEY,
    studio_id UUID REFERENCES studios(studio_id),
    min_wall_thickness FLOAT,
    actual_shrinkage_rate FLOAT,
    max_overhang_angle FLOAT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**验收**: 
- 表创建成功
- 外键约束生效

#### Q1.2.4 Migration 003 - idempotency_keys 表
**文件**: `backend/alembic/versions/003_idempotency_keys.py`

**表结构**:
```sql
CREATE TABLE idempotency_keys (
    key VARCHAR(64) PRIMARY KEY,
    resource_id VARCHAR(36),
    resource_type VARCHAR(50),
    response_body JSONB,
    created_at TIMESTAMP,
    expires_at TIMESTAMP
);
CREATE INDEX idx_idempotency_expires ON idempotency_keys(expires_at);
```

**验收**:
- 幂等性中间件测试：相同 key 返回相同 order_id

#### Q1.2.5 Migration 004 - tasks 持久化表
**文件**: `backend/alembic/versions/004_tasks_table.py`

**表结构**:
```sql
CREATE TABLE tasks (
    task_id VARCHAR(36) PRIMARY KEY,
    state VARCHAR(20) NOT NULL,
    payload JSONB,
    result_uri VARCHAR(500),
    progress INT DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
CREATE INDEX idx_tasks_state ON tasks(state);
CREATE INDEX idx_tasks_created ON tasks(created_at DESC);
```

**验收**:
- Redis flushdb 后任务状态仍可查询

#### Q1.2.6 CI 中的迁移测试
**文件**: `.github/workflows/test.yml`（新建）

**流程**:
1. 启动 Postgres 容器
2. 运行 `alembic upgrade head`
3. 运行 `alembic downgrade -1`
4. 再次 `alembic upgrade head`
5. 运行单元测试

**验收**: GitHub Actions 绿灯

### Q1.3 加密字段统一

#### Q1.3.1 实现 EncryptedStr TypeDecorator
**文件**: `backend/app/models/types.py`（扩展）

**实现**:
```python
from sqlalchemy import TypeDecorator, String
from app.core.crypto import get_crypto

class EncryptedStr(TypeDecorator):
    impl = String
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        if value is not None:
            return get_crypto().encrypt(value)
        return value
    
    def process_result_value(self, value, dialect):
        if value is not None:
            return get_crypto().decrypt(value)
        return value
```

**修改实体模型**:
- `User.phone_encrypted` 改用 `EncryptedStr(500)`
- 添加 `User.email_encrypted: Mapped[Optional[str]] = mapped_column(EncryptedStr(500))`
- 添加 `User.address_encrypted: Mapped[Optional[str]] = mapped_column(EncryptedStr(1000))`

**验收**:
```python
user = User(phone_encrypted="13912345678")
# DB 中存储密文
# model_dump() 返回明文 "13912345678"
```

#### Q1.3.2 Pepper 轮换脚本
**文件**: `scripts/rotate_pepper.py`

**功能**:
1. 读取新旧两个 pepper
2. 批量读取所有 User 记录
3. 用旧 pepper 解密，用新 pepper 重新加密
4. 回填 `phone_hash`（基于新 pepper）
5. 7 天窗口期支持双 pepper 验证

**验收**:
- 轮换后用户仍可正常登录
- 新注册用户使用新 pepper

## 依赖关系

```
Q1.1.1 (Docker) ──┐
                  ├──> Q1.1.2 (Config) ──> Q1.1.3 (Entities) ──> Q1.2.1 (Alembic Init)
Q1.1.4 (迁移脚本)──┘                                                    │
                                                                        ├──> Q1.2.2~Q1.2.5 (Migrations)
                                                                        │
Q1.3.1 (EncryptedStr) ───────────────────────────────────────────────┘
                                │
                                └──> Q1.3.2 (Pepper Rotation)
                                       │
                                       └──> Q1.2.6 (CI 测试)
```

## 风险与缓解

### 风险 1: 数据迁移丢失
**缓解**: 
- 迁移前完整备份 SQLite
- 迁移脚本添加事务回滚
- 验证步骤：对比记录总数、关键字段抽样

### 风险 2: pgvector 版本不兼容
**缓解**:
- 使用官方 `pgvector/pgvector:pg16` 镜像
- requirements.txt 固定 `pgvector==0.2.5`
- 提前测试 ivfflat 索引创建

### 风险 3: Alembic autogenerate 误判
**缓解**:
- 手动审查生成的迁移文件
- 先在 staging 数据库测试
- 保留 downgrade 函数

### 风险 4: 加密性能下降
**缓解**:
- EncryptedStr 仅用于低频字段（phone/email/address）
- 高频查询走 hash 索引而非解密
- 添加性能测试基准

## 测试策略

### 单元测试
- [ ] `test_vector_type.py`: Vector 类型序列化/反序列化
- [ ] `test_encrypted_str.py`: 加密/解密正确性
- [ ] `test_migrations.py`: 每个迁移的 upgrade/downgrade

### 集成测试
- [ ] `test_postgres_connection.py`: 连接池、事务隔离
- [ ] `test_pgvector_search.py`: embedding 向量检索准确性
- [ ] `test_data_migration.py`: SQLite → Postgres 完整性

### 性能测试
- [ ] 1000 条 embedding 检索 < 20ms (P95)
- [ ] 加密字段读写延迟 < 5ms 增量

## 时间估算

| 任务 | 预计时间 | 优先级 |
|------|----------|--------|
| Q1.1.1 | 0.5h | P0 |
| Q1.1.2 | 0.5h | P0 |
| Q1.1.3 | 2h | P0 |
| Q1.1.4 | 3h | P0 |
| Q1.2.1 | 1h | P0 |
| Q1.2.2 | 2h | P0 |
| Q1.2.3-5 | 1.5h | P0 |
| Q1.2.6 | 2h | P0 |
| Q1.3.1 | 2h | P0 |
| Q1.3.2 | 1.5h | P1 |
| 测试编写 | 4h | P0 |
| **总计** | **20h** | **约 2.5 工作日** |

## 验收标准

### 最终验收清单
- [ ] Docker Compose 一键启动 Postgres 16 + pgvector
- [ ] 应用默认连接 Postgres，SQLite 作为测试后备
- [ ] `design_templates.embedding` 为 vector(1536) 类型
- [ ] 所有 JSON 列在 Postgres 下为 JSONB
- [ ] SQLite 演示数据成功迁移到 Postgres
- [ ] Alembic 迁移历史完整，可前滚后滚
- [ ] 新增 3 张表（studio_craft_overrides, idempotency_keys, tasks）
- [ ] EncryptedStr 自动加解密生效
- [ ] CI 管道包含迁移测试
- [ ] 所有单元测试通过
- [ ] 性能指标达标

## 后续工作接口

完成 Q1 后，为 Q2（Redis Streams）准备：
- `tasks` 表已就绪，可与 Redis 双写
- `idempotency_keys` 表支持幂等性中间件
- Postgres 异步连接池已优化

完成 Q1 后，为 Q3（3D 模型）准备：
- `design_templates.embedding` 向量检索已可用
- ivfflat 索引已创建，可直接导入 30 个模板
