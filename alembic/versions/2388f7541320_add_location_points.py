"""add location_points

Revision ID: 2388f7541320
Revises: 8dccde8b2fe5
Create Date: 2026-06-14 02:25:17.541300

Note: autogenerate also emitted spurious NUMERIC->UUID alter_column statements
for the existing tables (a SQLite reflection artifact — see earlier migrations).
Those are removed; this migration only adds location_points.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2388f7541320'
down_revision: Union[str, None] = '8dccde8b2fe5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'location_points',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('backup_id', sa.Uuid(), nullable=False),
        sa.Column('location_identifier', sa.String(length=255), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('altitude', sa.Float(), nullable=True),
        sa.Column('speed', sa.Float(), nullable=True),
        sa.Column('horizontal_accuracy', sa.Float(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['backup_id'], ['backups.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('location_points', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_location_points_backup_id'), ['backup_id'], unique=False)
        batch_op.create_index(
            batch_op.f('ix_location_points_location_identifier'), ['location_identifier'], unique=False
        )
        batch_op.create_index(batch_op.f('ix_location_points_recorded_at'), ['recorded_at'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('location_points', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_location_points_recorded_at'))
        batch_op.drop_index(batch_op.f('ix_location_points_location_identifier'))
        batch_op.drop_index(batch_op.f('ix_location_points_backup_id'))
    op.drop_table('location_points')
