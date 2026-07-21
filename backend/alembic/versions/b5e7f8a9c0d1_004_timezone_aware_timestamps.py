"""004_timezone_aware_timestamps

将所有 DateTime 列迁移为 timezone-aware (UTC)。

Revision ID: b5e7f8a9c0d1
Revises: a1b2c3d4e5f6
Create Date: 2026-06-22 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5e7f8a9c0d1'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级：所有 DateTime 列 → DateTime(timezone=True)

    使用 AT TIME ZONE 'UTC' 确保已存储的 naive timestamp 被解释为 UTC。
    执行前提：本地环境需安装 asyncpg + alembic，且 Postgres 可连接。
    """

    # users 表
    op.alter_column('users', 'created_at',
                    type_=sa.DateTime(timezone=True),
                    postgresql_using="created_at AT TIME ZONE 'UTC'",
                    existing_nullable=False)
    op.alter_column('users', 'updated_at',
                    type_=sa.DateTime(timezone=True),
                    postgresql_using="updated_at AT TIME ZONE 'UTC'",
                    existing_nullable=False)

    # studios 表
    op.alter_column('studios', 'created_at',
                    type_=sa.DateTime(timezone=True),
                    postgresql_using="created_at AT TIME ZONE 'UTC'",
                    existing_nullable=False)
    op.alter_column('studios', 'updated_at',
                    type_=sa.DateTime(timezone=True),
                    postgresql_using="updated_at AT TIME ZONE 'UTC'",
                    existing_nullable=False)

    # sessions 表
    op.alter_column('sessions', 'created_at',
                    type_=sa.DateTime(timezone=True),
                    postgresql_using="created_at AT TIME ZONE 'UTC'",
                    existing_nullable=False)
    op.alter_column('sessions', 'updated_at',
                    type_=sa.DateTime(timezone=True),
                    postgresql_using="updated_at AT TIME ZONE 'UTC'",
                    existing_nullable=False)

    # session_messages 表
    op.alter_column('session_messages', 'created_at',
                    type_=sa.DateTime(timezone=True),
                    postgresql_using="created_at AT TIME ZONE 'UTC'",
                    existing_nullable=False)

    # design_templates 表
    op.alter_column('design_templates', 'created_at',
                    type_=sa.DateTime(timezone=True),
                    postgresql_using="created_at AT TIME ZONE 'UTC'",
                    existing_nullable=False)

    # designs 表
    op.alter_column('designs', 'created_at',
                    type_=sa.DateTime(timezone=True),
                    postgresql_using="created_at AT TIME ZONE 'UTC'",
                    existing_nullable=False)
    op.alter_column('designs', 'updated_at',
                    type_=sa.DateTime(timezone=True),
                    postgresql_using="updated_at AT TIME ZONE 'UTC'",
                    existing_nullable=False)

    # design_versions 表
    op.alter_column('design_versions', 'created_at',
                    type_=sa.DateTime(timezone=True),
                    postgresql_using="created_at AT TIME ZONE 'UTC'",
                    existing_nullable=False)

    # orders 表
    op.alter_column('orders', 'created_at',
                    type_=sa.DateTime(timezone=True),
                    postgresql_using="created_at AT TIME ZONE 'UTC'",
                    existing_nullable=False)
    op.alter_column('orders', 'updated_at',
                    type_=sa.DateTime(timezone=True),
                    postgresql_using="updated_at AT TIME ZONE 'UTC'",
                    existing_nullable=False)

    # order_logs 表
    op.alter_column('order_logs', 'created_at',
                    type_=sa.DateTime(timezone=True),
                    postgresql_using="created_at AT TIME ZONE 'UTC'",
                    existing_nullable=False)

    # studio_craft_overrides 表
    op.alter_column('studio_craft_overrides', 'created_at',
                    type_=sa.DateTime(timezone=True),
                    postgresql_using="created_at AT TIME ZONE 'UTC'",
                    existing_nullable=False)
    op.alter_column('studio_craft_overrides', 'updated_at',
                    type_=sa.DateTime(timezone=True),
                    postgresql_using="updated_at AT TIME ZONE 'UTC'",
                    existing_nullable=False)

    # idempotency_keys 表
    op.alter_column('idempotency_keys', 'created_at',
                    type_=sa.DateTime(timezone=True),
                    postgresql_using="created_at AT TIME ZONE 'UTC'",
                    existing_nullable=False)
    op.alter_column('idempotency_keys', 'expires_at',
                    type_=sa.DateTime(timezone=True),
                    postgresql_using="expires_at AT TIME ZONE 'UTC'",
                    existing_nullable=False)

    # tasks 表
    op.alter_column('tasks', 'created_at',
                    type_=sa.DateTime(timezone=True),
                    postgresql_using="created_at AT TIME ZONE 'UTC'",
                    existing_nullable=False)
    op.alter_column('tasks', 'updated_at',
                    type_=sa.DateTime(timezone=True),
                    postgresql_using="updated_at AT TIME ZONE 'UTC'",
                    existing_nullable=False)

    # uploads 表
    op.alter_column('uploads', 'created_at',
                    type_=sa.DateTime(timezone=True),
                    postgresql_using="created_at AT TIME ZONE 'UTC'",
                    existing_nullable=False)
    op.alter_column('uploads', 'updated_at',
                    type_=sa.DateTime(timezone=True),
                    postgresql_using="updated_at AT TIME ZONE 'UTC'",
                    existing_nullable=False)


def downgrade() -> None:
    """降级：所有 DateTime(timezone=True) 列 → DateTime (naive)

    警告：时区信息会丢失，不建议回退。
    """

    # users 表
    op.alter_column('users', 'created_at',
                    type_=sa.DateTime(timezone=False),
                    existing_nullable=False)
    op.alter_column('users', 'updated_at',
                    type_=sa.DateTime(timezone=False),
                    existing_nullable=False)

    # studios 表
    op.alter_column('studios', 'created_at',
                    type_=sa.DateTime(timezone=False),
                    existing_nullable=False)
    op.alter_column('studios', 'updated_at',
                    type_=sa.DateTime(timezone=False),
                    existing_nullable=False)

    # sessions 表
    op.alter_column('sessions', 'created_at',
                    type_=sa.DateTime(timezone=False),
                    existing_nullable=False)
    op.alter_column('sessions', 'updated_at',
                    type_=sa.DateTime(timezone=False),
                    existing_nullable=False)

    # session_messages 表
    op.alter_column('session_messages', 'created_at',
                    type_=sa.DateTime(timezone=False),
                    existing_nullable=False)

    # design_templates 表
    op.alter_column('design_templates', 'created_at',
                    type_=sa.DateTime(timezone=False),
                    existing_nullable=False)

    # designs 表
    op.alter_column('designs', 'created_at',
                    type_=sa.DateTime(timezone=False),
                    existing_nullable=False)
    op.alter_column('designs', 'updated_at',
                    type_=sa.DateTime(timezone=False),
                    existing_nullable=False)

    # design_versions 表
    op.alter_column('design_versions', 'created_at',
                    type_=sa.DateTime(timezone=False),
                    existing_nullable=False)

    # orders 表
    op.alter_column('orders', 'created_at',
                    type_=sa.DateTime(timezone=False),
                    existing_nullable=False)
    op.alter_column('orders', 'updated_at',
                    type_=sa.DateTime(timezone=False),
                    existing_nullable=False)

    # order_logs 表
    op.alter_column('order_logs', 'created_at',
                    type_=sa.DateTime(timezone=False),
                    existing_nullable=False)

    # studio_craft_overrides 表
    op.alter_column('studio_craft_overrides', 'created_at',
                    type_=sa.DateTime(timezone=False),
                    existing_nullable=False)
    op.alter_column('studio_craft_overrides', 'updated_at',
                    type_=sa.DateTime(timezone=False),
                    existing_nullable=False)

    # idempotency_keys 表
    op.alter_column('idempotency_keys', 'created_at',
                    type_=sa.DateTime(timezone=False),
                    existing_nullable=False)
    op.alter_column('idempotency_keys', 'expires_at',
                    type_=sa.DateTime(timezone=False),
                    existing_nullable=False)

    # tasks 表
    op.alter_column('tasks', 'created_at',
                    type_=sa.DateTime(timezone=False),
                    existing_nullable=False)
    op.alter_column('tasks', 'updated_at',
                    type_=sa.DateTime(timezone=False),
                    existing_nullable=False)

    # uploads 表
    op.alter_column('uploads', 'created_at',
                    type_=sa.DateTime(timezone=False),
                    existing_nullable=False)
    op.alter_column('uploads', 'updated_at',
                    type_=sa.DateTime(timezone=False),
                    existing_nullable=False)
