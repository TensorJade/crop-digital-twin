"""M1 SQL tables with logical references, indexes and immutable event revisions."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Float, Index, Numeric, String, Text, Uuid, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Metadata owner for explicit Alembic migrations."""


class PlotRecord(Base):
    """Manual plot area and WGS84 position; geometry is a future module."""

    __tablename__ = "plots"
    __table_args__ = (
        CheckConstraint("area_mu > 0 AND area_mu <= 1000000", name="ck_plots_area"),
        CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_plots_latitude"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_plots_longitude"),
        Index("idx_plots_created_at", "created_at", "id"),
        Index("idx_plots_organization_id", "organization_id", "created_at", "id"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    area_mu: Mapped[Decimal] = mapped_column(Numeric(16, 6))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    organization_id: Mapped[UUID | None] = mapped_column(Uuid)


class SeasonRecord(Base):
    """Logical plot reference and non-overlapping rice-season dates."""

    __tablename__ = "seasons"
    __table_args__ = (
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="ck_seasons_dates"),
        CheckConstraint(
            "establishment_method IN ('direct_sowing', 'transplanting')",
            name="ck_seasons_establishment",
        ),
        Index("idx_seasons_plot_id", "plot_id", "start_date"),
        Index(
            "uniq_seasons_open_plot",
            "plot_id",
            unique=True,
            sqlite_where=text("end_date IS NULL"),
            postgresql_where=text("end_date IS NULL"),
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    plot_id: Mapped[UUID] = mapped_column(Uuid)
    start_date: Mapped[date]
    end_date: Mapped[date | None]
    establishment_method: Mapped[str] = mapped_column(String(24))
    variety_name: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EventRecord(Base):
    """Original and normalized operation quantities plus an append-only revision link."""

    __tablename__ = "management_events"
    __table_args__ = (
        CheckConstraint("revision >= 1", name="ck_management_events_revision"),
        CheckConstraint("quantity IS NULL OR quantity > 0", name="ck_management_events_quantity"),
        Index("idx_management_events_season_date", "season_id", "occurred_on", "id"),
        Index("uniq_management_events_replaces", "replaces_event_id", unique=True),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    season_id: Mapped[UUID] = mapped_column(Uuid)
    event_type: Mapped[str] = mapped_column(String(24))
    occurred_on: Mapped[date]
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    unit: Mapped[str | None] = mapped_column(String(16))
    normalized_quantity: Mapped[Decimal | None] = mapped_column(Numeric(24, 6))
    normalized_unit: Mapped[str | None] = mapped_column(String(16))
    material_name: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revision: Mapped[int] = mapped_column(default=1)
    replaces_event_id: Mapped[UUID | None] = mapped_column(Uuid)
    correction_reason: Mapped[str | None] = mapped_column(String(240))
