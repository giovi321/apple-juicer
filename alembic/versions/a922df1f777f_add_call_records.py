"""add call_records

Revision ID: a922df1f777f
Revises: bd9c1b9d4058
Create Date: 2026-06-14 01:07:04.050596

Note: autogenerate also emitted spurious NUMERIC->UUID alter_column statements
for every existing table. Those are a SQLite reflection artifact (SQLite has no
native UUID type, so the baseline's UUID columns reflect back as NUMERIC); on
Postgres the columns are already UUID. They have been removed — this migration
only adds the call_records table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a922df1f777f'
down_revision: Union[str, None] = 'bd9c1b9d4058'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'call_records',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('backup_id', sa.Uuid(), nullable=False),
        sa.Column('call_identifier', sa.String(length=255), nullable=False),
        sa.Column('address', sa.String(length=255), nullable=True),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('is_outgoing', sa.Boolean(), nullable=False),
        sa.Column('answered', sa.Boolean(), nullable=False),
        sa.Column('service', sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(['backup_id'], ['backups.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('call_records', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_call_records_backup_id'), ['backup_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_call_records_call_identifier'), ['call_identifier'], unique=False)
        batch_op.create_index(batch_op.f('ix_call_records_occurred_at'), ['occurred_at'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('call_records', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_call_records_occurred_at'))
        batch_op.drop_index(batch_op.f('ix_call_records_call_identifier'))
        batch_op.drop_index(batch_op.f('ix_call_records_backup_id'))
    op.drop_table('call_records')
