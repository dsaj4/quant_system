"""narrative runs

Revision ID: 20260603_000003
Revises: 20260602_000002
Create Date: 2026-06-03 00:00:00.000000+00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = "20260603_000003"
down_revision: str | Sequence[str] | None = "20260602_000002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "narrativerun",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("backtest_run_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "succeeded", "degraded", "failed", "reviewed", name="narrativestatus"),
            nullable=False,
        ),
        sa.Column("is_smoke_test", sa.Boolean(), nullable=False),
        sa.Column("provider", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("provider_model", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("analysis_date", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("quant_rating", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("quant_rating_inputs", sa.JSON(), nullable=True),
        sa.Column("target_scope", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("target_summary", sa.JSON(), nullable=True),
        sa.Column("ticker_mapping", sa.JSON(), nullable=True),
        sa.Column("coverage_summary", sa.JSON(), nullable=True),
        sa.Column("input_summary", sa.JSON(), nullable=True),
        sa.Column("provider_structured_summary", sa.JSON(), nullable=True),
        sa.Column("provider_raw_suggestion", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("provider_conflict", sa.Boolean(), nullable=False),
        sa.Column("degraded_reasons", sa.JSON(), nullable=True),
        sa.Column("degraded_acknowledged_by", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("degraded_acknowledged_at", sa.DateTime(), nullable=True),
        sa.Column("ai_draft_payload", sa.JSON(), nullable=True),
        sa.Column("reviewed_payload", sa.JSON(), nullable=True),
        sa.Column("reviewed_by", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("review_note", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("error_message", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["backtest_run_id"], ["backtestrun.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("narrativerun", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_narrativerun_analysis_date"), ["analysis_date"], unique=False)
        batch_op.create_index(batch_op.f("ix_narrativerun_backtest_run_id"), ["backtest_run_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_narrativerun_is_smoke_test"), ["is_smoke_test"], unique=False)
        batch_op.create_index(batch_op.f("ix_narrativerun_provider"), ["provider"], unique=False)
        batch_op.create_index(batch_op.f("ix_narrativerun_provider_conflict"), ["provider_conflict"], unique=False)
        batch_op.create_index(batch_op.f("ix_narrativerun_quant_rating"), ["quant_rating"], unique=False)
        batch_op.create_index(batch_op.f("ix_narrativerun_status"), ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_narrativerun_target_scope"), ["target_scope"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("narrativerun", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_narrativerun_target_scope"))
        batch_op.drop_index(batch_op.f("ix_narrativerun_status"))
        batch_op.drop_index(batch_op.f("ix_narrativerun_quant_rating"))
        batch_op.drop_index(batch_op.f("ix_narrativerun_provider_conflict"))
        batch_op.drop_index(batch_op.f("ix_narrativerun_provider"))
        batch_op.drop_index(batch_op.f("ix_narrativerun_is_smoke_test"))
        batch_op.drop_index(batch_op.f("ix_narrativerun_backtest_run_id"))
        batch_op.drop_index(batch_op.f("ix_narrativerun_analysis_date"))
    op.drop_table("narrativerun")
