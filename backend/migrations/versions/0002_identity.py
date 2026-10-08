"""Add scoped ownership, accounts, revocable sessions, login limits and audit records."""

import sqlalchemy as sa
from alembic import op

revision = "0002_identity"
down_revision = "0001_farm_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Preserve old farm records; ownership is assigned only by an explicit operation."""
    op.add_column("plots", sa.Column("organization_id", sa.Uuid(), nullable=True))
    op.create_index("idx_plots_organization_id", "plots", ["organization_id", "created_at", "id"])
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(80), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('owner', 'operator', 'viewer')", name="ck_users_role"),
    )
    op.create_index("uniq_users_username", "users", ["username"], unique=True)
    op.create_index("idx_users_organization_id", "users", ["organization_id", "created_at", "id"])
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_digest", sa.String(64), nullable=False),
        sa.Column("csrf_token", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("expires_at > created_at", name="ck_user_sessions_dates"),
    )
    op.create_index(
        "uniq_user_sessions_token_digest", "user_sessions", ["token_digest"], unique=True
    )
    op.create_index("idx_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("idx_user_sessions_expires_at", "user_sessions", ["expires_at"])
    op.create_table(
        "login_limits",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_key", sa.String(64), nullable=False),
        sa.Column("failures", sa.Integer(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("failures BETWEEN 0 AND 5", name="ck_login_limits_failures"),
    )
    op.create_index("uniq_login_limits_source_key", "login_limits", ["source_key"], unique=True)
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_audit_events_organization_id", "audit_events", ["organization_id", "created_at", "id"]
    )


def downgrade() -> None:
    """Destructive downgrade is an explicit operator action, never an application step."""
    for table in ("audit_events", "login_limits", "user_sessions", "users", "organizations"):
        op.drop_table(table)
    op.drop_index("idx_plots_organization_id", table_name="plots")
    op.drop_column("plots", "organization_id")
