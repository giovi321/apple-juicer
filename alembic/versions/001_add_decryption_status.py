"""Add decryption status fields to backups table

Revision ID: 001_add_decryption_status
Revises: 
Create Date: 2025-12-21 22:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_add_decryption_status'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('backups', sa.Column('decryption_status', sa.Enum('pending', 'decrypting', 'decrypted', 'failed', name='decryptionstatus'), nullable=False, server_default='pending'))
    op.add_column('backups', sa.Column('decrypted_path', sa.String(1024), nullable=True))
    op.add_column('backups', sa.Column('decryption_error', sa.Text(), nullable=True))
    op.add_column('backups', sa.Column('decrypted_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('backups', 'decrypted_at')
    op.drop_column('backups', 'decryption_error')
    op.drop_column('backups', 'decrypted_path')
    op.drop_column('backups', 'decryption_status')
