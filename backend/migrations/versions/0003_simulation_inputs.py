"""Add typed input assets and immutable season snapshots, preserving M1/M2 data."""

import sqlalchemy as sa
from alembic import op

revision = "0003_simulation_inputs"
down_revision = "0002_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add data tables only; never import runtime ORM definitions into a frozen migration."""
    op.create_table(
        "input_assets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("plot_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("source", sa.String(1000), nullable=False),
        sa.Column("source_license", sa.String(300), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind IN ('soil', 'crop', 'weather')", name="ck_input_assets_kind"),
        sa.CheckConstraint(
            "(kind = 'crop' AND plot_id IS NULL) OR "
            "(kind IN ('soil', 'weather') AND plot_id IS NOT NULL)",
            name="ck_input_assets_scope",
        ),
    )
    op.create_index(
        "idx_input_assets_organization_id",
        "input_assets",
        ["organization_id", "kind", "plot_id", "created_at", "id"],
    )
    op.create_table(
        "simulation_inputs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("season_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("version >= 1", name="ck_simulation_inputs_version"),
    )
    op.create_index(
        "uniq_simulation_inputs_season_id",
        "simulation_inputs",
        ["season_id", "version"],
        unique=True,
    )
    op.create_index(
        "idx_simulation_inputs_organization_id",
        "simulation_inputs",
        ["organization_id", "season_id", "created_at", "id"],
    )


def downgrade() -> None:
    """Explicit destructive downgrade; never used on the application database."""
    op.drop_table("simulation_inputs")
    op.drop_table("input_assets")
