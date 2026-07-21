"""add_result_field_to_tasks

Revision ID: 138f01683ede
Revises: d1e2f3a4b5c6
Create Date: 2026-06-24 18:03:41.739047

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '138f01683ede'
down_revision: Union[str, Sequence[str], None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add result JSONB column to tasks table for dual-write strategy.

    This enables persistent storage of task results in PostgreSQL,
    preventing data loss when Redis restarts or evicts keys.
    """
    op.add_column(
        'tasks',
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )

    # Optional: Add index for faster queries on completed tasks
    # op.create_index('idx_tasks_result_not_null', 'tasks', ['task_id'],
    #                 postgresql_where=sa.text("result IS NOT NULL"))


def downgrade() -> None:
    """Remove result column from tasks table."""
    # op.drop_index('idx_tasks_result_not_null', table_name='tasks', postgresql_where=sa.text("result IS NOT NULL"))
    op.drop_column('tasks', 'result')
