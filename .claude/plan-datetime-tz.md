# 计划：datetime.utcnow → timezone-aware UTC

## 背景与动机
报告「八、1」的技术债：全项目用 `datetime.utcnow()`（naive，无时区），存入 `DateTime`（无 tz）列。
风险：naive 与 aware datetime 比较会抛 `TypeError`；跨时区部署时时间语义不明确。
本次统一改为 timezone-aware UTC（`datetime.now(timezone.utc)`）+ `DateTime(timezone=True)` 列。

## 影响面（已扫描确认）
- **13 张表**全部时间字段（entities.py，23 处 DateTime 列定义）
- **50 处** `datetime.utcnow()` 调用，分布在 11 个文件
- 1 个 in-memory dataclass（`Alert`，alerting_service.py）
- JWT exp 计算（auth.py，2 处）
- `.isoformat()` 序列化（task_service / alerts / logistics 等）→ aware 后输出带 `+00:00`

## 关键约束（本环境）
- 本地**无 asyncpg、无 alembic、无 Postgres**，仅 aiosqlite + SQLAlchemy。
- 因此 `app.main` 无法本地 import，alembic 迁移**无法本地执行**。
- 可验证：不依赖 DB 的单测（27+ 通过）、`entities.py` 独立 import、time helper。
- 迁移脚本按 Postgres 语义编写，标注需在有 DB 的环境执行。

## 实施步骤

### 1. 新增 `app/core/time.py`
```python
from datetime import datetime, timezone
def utcnow() -> datetime:
    """timezone-aware UTC now，替代裸 datetime.utcnow()"""
    return datetime.now(timezone.utc)
```

### 2. 改 `app/models/entities.py`
- `from app.core.time import utcnow`
- 所有 `DateTime` → `DateTime(timezone=True)`（23 处）
- 所有 `default=datetime.utcnow` → `default=utcnow`
- 所有 `onupdate=datetime.utcnow` → `onupdate=utcnow`
- 保留 `from datetime import datetime` 仅用于类型注解

### 3. 替换 50 处调用站点（11 文件）
统一 `datetime.utcnow()` → `utcnow()`，import 改为 `from app.core.time import utcnow`：
- api/: alerts, logistics, payments, sessions, studio_onboarding, studio_orders
- services/: auth, order/order_service, tasks/task_service, alerting/alerting_service

### 4. 新增迁移 `alembic/versions/xxxx_004_timezone_aware_timestamps.py`
- `down_revision = 'a1b2c3d4e5f6'`（当前 head）
- 对 13 表每个时间列：`op.alter_column(..., type_=sa.DateTime(timezone=True), postgresql_using="<col> AT TIME ZONE 'UTC'")`
- downgrade 反向 `DateTime(timezone=False)`

### 5. 验证
- `pytest tests/ -q --ignore=tests/test_craft_check.py`（不依赖 DB 的用例应仍全绿）
- `python -c "from app.models.entities import Base; print(len(Base.metadata.tables))"` 确认模型可独立 import
- `python -c "from app.core.time import utcnow; print(utcnow().tzinfo)"` 确认 aware
- 文档标注：alembic 迁移需在装有 asyncpg+alembic 的环境 `alembic upgrade head` 执行

## 不做 / 留意
- 不改前端：`new Date(s)` 能正确解析带 `+00:00` 的 ISO，无需改动。
- `Alert` dataclass 也换 `utcnow()` 保持一致，避免与 DB datetime 混比。
- JWT exp：jose 对 aware/naive 都可编码，换 aware 更正确。

## 验收
- 单测无回归；模型独立 import 成功；helper 返回 aware。
- 报告追加「附录 B」记录本次迁移与执行说明。
