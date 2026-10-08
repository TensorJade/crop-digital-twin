"""Two append-only, scoped input tables; typed payloads are checked before persistence."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, CheckConstraint, DateTime, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from crop_twin.infrastructure.database.identity_models import Base as Base


class InputAssetRecord(Base):
    """An explicitly typed soil, crop or weather version."""

    __tablename__ = "input_assets"
    __table_args__ = (
        CheckConstraint("kind IN ('soil', 'crop', 'weather')", name="ck_input_assets_kind"),
        CheckConstraint(
            "(kind = 'crop' AND plot_id IS NULL) OR "
            "(kind IN ('soil', 'weather') AND plot_id IS NOT NULL)",
            name="ck_input_assets_scope",
        ),
        Index(
            "idx_input_assets_organization_id",
            "organization_id",
            "kind",
            "plot_id",
            "created_at",
            "id",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(Uuid)
    plot_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    kind: Mapped[str] = mapped_column(String(16))
    name: Mapped[str] = mapped_column(String(100))
    source: Mapped[str] = mapped_column(String(1000))
    source_license: Mapped[str] = mapped_column(String(300))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    content_hash: Mapped[str] = mapped_column(String(64))
    actor_user_id: Mapped[UUID] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SimulationInputRecord(Base):
    """A full frozen season input, whose list response omits the large payload."""

    __tablename__ = "simulation_inputs"
    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_simulation_inputs_version"),
        Index("uniq_simulation_inputs_season_id", "season_id", "version", unique=True),
        Index(
            "idx_simulation_inputs_organization_id",
            "organization_id",
            "season_id",
            "created_at",
            "id",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(Uuid)
    season_id: Mapped[UUID] = mapped_column(Uuid)
    version: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    content_hash: Mapped[str] = mapped_column(String(64))
    actor_user_id: Mapped[UUID] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
