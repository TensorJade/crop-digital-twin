"""Create the M1 farm tables. Logical references are enforced by application transactions."""

import sqlalchemy as sa
from alembic import op

revision = "0001_farm_records"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Establish manual plots, rice seasons and retained operation revisions."""
    op.create_table(
        "plots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("area_mu", sa.Numeric(16, 6), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("area_mu > 0 AND area_mu <= 1000000", name="ck_plots_area"),
        sa.CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_plots_latitude"),
        sa.CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_plots_longitude"),
    )
    op.create_index("idx_plots_created_at", "plots", ["created_at", "id"])
    op.create_table(
        "seasons",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("plot_id", sa.Uuid(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("establishment_method", sa.String(24), nullable=False),
        sa.Column("variety_name", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("end_date IS NULL OR end_date >= start_date", name="ck_seasons_dates"),
        sa.CheckConstraint(
            "establishment_method IN ('direct_sowing', 'transplanting')",
            name="ck_seasons_establishment",
        ),
    )
    op.create_index("idx_seasons_plot_id", "seasons", ["plot_id", "start_date"])
    op.create_index(
        "uniq_seasons_open_plot",
        "seasons",
        ["plot_id"],
        unique=True,
        sqlite_where=sa.text("end_date IS NULL"),
        postgresql_where=sa.text("end_date IS NULL"),
    )
    op.create_table(
        "management_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("season_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(24), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=True),
        sa.Column("unit", sa.String(16), nullable=True),
        sa.Column("normalized_quantity", sa.Numeric(24, 6), nullable=True),
        sa.Column("normalized_unit", sa.String(16), nullable=True),
        sa.Column("material_name", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("replaces_event_id", sa.Uuid(), nullable=True),
        sa.Column("correction_reason", sa.String(240), nullable=True),
        sa.CheckConstraint("revision >= 1", name="ck_management_events_revision"),
        sa.CheckConstraint(
            "quantity IS NULL OR quantity > 0", name="ck_management_events_quantity"
        ),
    )
    op.create_index(
        "idx_management_events_season_date", "management_events", ["season_id", "occurred_on", "id"]
    )
    op.create_index(
        "uniq_management_events_replaces", "management_events", ["replaces_event_id"], unique=True
    )


def downgrade() -> None:
    """Remove M1 tables only when explicitly requested by a migration operator."""
    op.drop_table("management_events")
    op.drop_table("seasons")
    op.drop_table("plots")
