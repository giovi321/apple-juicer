"""add safari_visits

Revision ID: 8dccde8b2fe5
Revises: a922df1f777f
Create Date: 2026-06-14 01:58:02.587675

Note: autogenerate also emitted spurious NUMERIC->UUID alter_column statements
for the existing tables (a SQLite reflection artifact — see the baseline and
call_records migrations). Those are removed; this migration only adds
safari_visits.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8dccde8b2fe5'
down_revision: Union[str, None] = 'a922df1f777f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'safari_visits',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('backup_id', sa.Uuid(), nullable=False),
        sa.Column('visit_identifier', sa.String(length=255), nullable=False),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('title', sa.String(length=1024), nullable=True),
        sa.Column('visited_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('visit_count', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['backup_id'], ['backups.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('safari_visits', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_safari_visits_backup_id'), ['backup_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_safari_visits_visit_identifier'), ['visit_identifier'], unique=False)
        batch_op.create_index(batch_op.f('ix_safari_visits_visited_at'), ['visited_at'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('safari_visits', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_safari_visits_visited_at'))
        batch_op.drop_index(batch_op.f('ix_safari_visits_visit_identifier'))
        batch_op.drop_index(batch_op.f('ix_safari_visits_backup_id'))
    op.drop_table('safari_visits')
