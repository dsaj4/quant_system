"""paper run monitoring

Revision ID: 20260602_000002
Revises: 20260602_000001
Create Date: 2026-06-02 12:30:00.000000+00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260602_000002"
down_revision: str | Sequence[str] | None = "20260602_000001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("paperrun", schema=None) as batch_op:
        batch_op.add_column(sa.Column("started_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("finished_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("paperrun", schema=None) as batch_op:
        batch_op.drop_column("finished_at")
        batch_op.drop_column("started_at")
