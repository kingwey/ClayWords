"""006_add_user_social_bindings

Revision ID: d1e2f3a4b5c6
Revises: c0d1e2f3a4b5
Create Date: 2026-06-23 16:00:00.000000

新增 users.social_bindings (JSONB, 默认空 dict)。
存储第三方账号绑定信息, 形如:
  {
    "wechat": {"openid": "...", "bound_at": "2026-..."},
    "feishu": {...}, "qq": {...}, "dingtalk": {...}, "douyin": {...}
  }
- 当前为演示绑定 (记录 mock openid + 时间); 生产环境替换为真实 OAuth 回调
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = 'c0d1e2f3a4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add social_bindings JSONB column with empty-dict default."""
    op.add_column(
        'users',
        sa.Column(
            'social_bindings',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='{}',
        ),
    )
    # 移除 server_default, 让应用层默认值生效 (与模型 default=dict 一致)
    op.alter_column('users', 'social_bindings', server_default=None)


def downgrade() -> None:
    """Drop social_bindings column."""
    op.drop_column('users', 'social_bindings')
