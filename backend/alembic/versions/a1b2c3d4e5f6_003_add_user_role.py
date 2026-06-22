"""003_add_user_role

Revision ID: a1b2c3d4e5f6
Revises: 86ad82ebb698
Create Date: 2026-06-22 11:30:00.000000

新增 users.role（user/studio/admin）与 users.studio_id（工作室用户关联）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '86ad82ebb698'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add role and studio_id to users."""
    op.add_column(
        'users',
        sa.Column('role', sa.String(length=20), nullable=False, server_default='user')
    )
    op.add_column(
        'users',
        sa.Column('studio_id', sa.String(length=36), nullable=True)
    )
    op.create_foreign_key(
        'fk_users_studio_id',
        'users', 'studios',
        ['studio_id'], ['studio_id']
    )
    # 移除 server_default，让应用层默认值生效（保持与模型一致）
    op.alter_column('users', 'role', server_default=None)


def downgrade() -> None:
    """Downgrade schema - Remove role and studio_id from users."""
    op.drop_constraint('fk_users_studio_id', 'users', type_='foreignkey')
    op.drop_column('users', 'studio_id')
    op.drop_column('users', 'role')
