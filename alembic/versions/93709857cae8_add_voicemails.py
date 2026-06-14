"""add voicemails

Revision ID: 93709857cae8
Revises: 2388f7541320
Create Date: 2026-06-14 02:31:15.225755

Note: autogenerate also emitted spurious NUMERIC->UUID alter_column statements
for the existing tables (a SQLite reflection artifact — see earlier migrations).
Those are removed; this migration only adds voicemails.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '93709857cae8'
down_revision: Union[str, None] = '2388f7541320'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'voicemails',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('backup_id', sa.Uuid(), nullable=False),
        sa.Column('voicemail_identifier', sa.String(length=255), nullable=False),
        sa.Column('sender', sa.String(length=255), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('trashed', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['backup_id'], ['backups.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('voicemails', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_voicemails_backup_id'), ['backup_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_voicemails_voicemail_identifier'), ['voicemail_identifier'], unique=False)
        batch_op.create_index(batch_op.f('ix_voicemails_received_at'), ['received_at'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('voicemails', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_voicemails_received_at'))
        batch_op.drop_index(batch_op.f('ix_voicemails_voicemail_identifier'))
        batch_op.drop_index(batch_op.f('ix_voicemails_backup_id'))
    op.drop_table('voicemails')
