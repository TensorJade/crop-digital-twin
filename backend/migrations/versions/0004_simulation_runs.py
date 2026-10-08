"""Add a persistent simulation task/result table; preserve all prior data."""

import sqlalchemy as sa
from alembic import op

revision = "0004_simulation_runs"
down_revision = "0003_simulation_inputs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Freeze explicit DDL, including lease and terminal result constraints."""
    op.create_table(
        "simulation_runs",
        *[
            sa.Column(name, sa.Uuid(), nullable=False, primary_key=name == "id")
            for name in (
                "id",
                "organization_id",
                "season_id",
                "input_id",
                "request_key",
                "actor_user_id",
            )
        ],
        sa.Column("model_code", sa.String(32), nullable=False),
        sa.Column("engine_version", sa.String(32), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_token", sa.Uuid(), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("result_hash", sa.String(64), nullable=True),
        sa.Column("result", sa.JSON(none_as_null=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')",
            name="ck_simulation_runs_status",
        ),
        sa.CheckConstraint("attempts BETWEEN 0 AND 3", name="ck_simulation_runs_attempts"),
        sa.CheckConstraint(
            "(status = 'running' AND lease_token IS NOT NULL AND lease_expires_at IS NOT NULL) OR "
            "(status != 'running' AND lease_token IS NULL AND lease_expires_at IS NULL)",
            name="ck_simulation_runs_lease",
        ),
        sa.CheckConstraint(
            "(status = 'succeeded' AND result IS NOT NULL AND result_hash IS NOT NULL "
            "AND error_code IS NULL) OR "
            "(status != 'succeeded' AND result_hash IS NULL)",
            name="ck_simulation_runs_result",
        ),
    )
    op.create_index(
        "uniq_simulation_runs_organization_id",
        "simulation_runs",
        ["organization_id", "request_key"],
        unique=True,
    )
    op.create_index(
        "idx_simulation_runs_organization_id",
        "simulation_runs",
        ["organization_id", "season_id", "created_at", "id"],
    )
    op.create_index(
        "idx_simulation_runs_status",
        "simulation_runs",
        ["status", "lease_expires_at", "created_at"],
    )


def downgrade() -> None:
    """Destructive isolated-test downgrade; never called by the runtime entrypoint."""
    op.drop_table("simulation_runs")
