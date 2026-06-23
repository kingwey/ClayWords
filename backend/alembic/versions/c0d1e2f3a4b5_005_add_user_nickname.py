"""005_add_user_nickname

Revision ID: c0d1e2f3a4b5
Revises: b5e7f8a9c0d1
Create Date: 2026-06-23 14:30:00.000000

新增 users.nickname (用户昵称, 可空)。
- 当前用户身份显示用脱敏手机号 (139****1234) 当昵称
- 新增字段后, 优先显示用户自定义昵称, 退化到脱敏手机号
- 字段非加密 (与昵称的展示用途相符), 长度上限 50 防止滥用
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c0d1e2f3a4b5'
down_revision: Union[str, Sequence[str], None] = 'b5e7f8a9c0d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nullable nickname column."""
    op.add_column(
        'users',
        sa.Column('nickname', sa.String(length=50), nullable=True)
    )


def downgrade() -> None:
    """Drop nickname column."""
    op.drop_column('users', 'nickname')
