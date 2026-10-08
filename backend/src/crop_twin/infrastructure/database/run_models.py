"""One SQL queue/result table with explicit constraints and logical references."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, CheckConstraint, DateTime, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from crop_twin.infrastructure.database.input_models import Base as Base


class SimulationRunRecord(Base):
    """Mutable processing state, immutable input reference and terminal result version."""

    __tablename__ = "simulation_runs"
    __table_args__ = (
        Index(
            "uniq_simulation_runs_organization_id", "organization_id", "request_key", unique=True
        ),
        Index(
            "idx_simulation_runs_organization_id",
            "organization_id",
            "season_id",
            "created_at",
            "id",
        ),
        Index("idx_simulation_runs_status", "status", "lease_expires_at", "created_at"),
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')",
            name="ck_simulation_runs_status",
        ),
        CheckConstraint("attempts BETWEEN 0 AND 3", name="ck_simulation_runs_attempts"),
        CheckConstraint(
            "(status = 'running' AND lease_token IS NOT NULL AND lease_expires_at IS NOT NULL) OR "
            "(status != 'running' AND lease_token IS NULL AND lease_expires_at IS NULL)",
            name="ck_simulation_runs_lease",
        ),
        CheckConstraint(
            "(status = 'succeeded' AND result IS NOT NULL AND result_hash IS NOT NULL "
            "AND error_code IS NULL) OR "
            "(status != 'succeeded' AND result_hash IS NULL)",
            name="ck_simulation_runs_result",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(Uuid)
    season_id: Mapped[UUID] = mapped_column(Uuid)
    input_id: Mapped[UUID] = mapped_column(Uuid)
    request_key: Mapped[UUID] = mapped_column(Uuid)
    actor_user_id: Mapped[UUID] = mapped_column(Uuid)
    model_code: Mapped[str] = mapped_column(String(32))
    engine_version: Mapped[str] = mapped_column(String(32))
    input_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))
    attempts: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    lease_token: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    result_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON(none_as_null=True), nullable=True)
