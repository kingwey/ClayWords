"""002_add_uploads_table

Revision ID: 86ad82ebb698
Revises: c845aee3c751
Create Date: 2026-06-21 17:58:22.692110

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '86ad82ebb698'
down_revision: Union[str, Sequence[str], None] = 'c845aee3c751'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add uploads table."""
    op.create_table('uploads',
    sa.Column('upload_id', sa.String(length=36), nullable=False),
    sa.Column('object_key', sa.String(length=500), nullable=False),
    sa.Column('file_name', sa.String(length=255), nullable=False),
    sa.Column('file_size', sa.Integer(), nullable=False),
    sa.Column('mime_type', sa.String(length=100), nullable=False),
    sa.Column('state', sa.String(length=20), nullable=False),
    sa.Column('scan_result', JSONB(), nullable=True),
    sa.Column('uploader_id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('upload_id'),
    sa.UniqueConstraint('object_key')
    )
    op.create_index('idx_uploads_created', 'uploads', ['created_at'], unique=False)
    op.create_index('idx_uploads_state', 'uploads', ['state'], unique=False)
    op.create_index('idx_uploads_uploader', 'uploads', ['uploader_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema - Remove uploads table."""
    op.drop_index('idx_uploads_uploader', table_name='uploads')
    op.drop_index('idx_uploads_state', table_name='uploads')
    op.drop_index('idx_uploads_created', table_name='uploads')
    op.drop_table('uploads')
