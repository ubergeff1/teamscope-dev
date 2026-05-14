"""
Actual hours and import log models.

Actual: Hours a consultant actually charged to a project in a given week.
  Imported from Float CSV exports (silent upsert — no approval workflow).
  week_start is always Monday.

ImportLog: Audit trail for every CSV/data import.
  Records source, timestamp, row counts, and any errors encountered.
"""
from sqlalchemy import Integer, String, Text, Numeric, Date, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base


class Actual(Base):
    __tablename__ = "actuals"
    __table_args__ = (UniqueConstraint("consultant_id", "project_id", "week_start"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    consultant_id: Mapped[int] = mapped_column(ForeignKey("consultants.id", ondelete="CASCADE"))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    week_start: Mapped[Date] = mapped_column(Date, nullable=False)  # Monday of the week
    hours: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="float")  # float | manual
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    consultant: Mapped["Consultant"] = relationship("Consultant")  # type: ignore
    project: Mapped["Project"] = relationship("Project")  # type: ignore


class ImportLog(Base):
    __tablename__ = "import_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # float_actuals | monday_projects | monday_delta
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    filename: Mapped[str | None] = mapped_column(String(255))
    rows_processed: Mapped[int] = mapped_column(Integer, default=0)
    rows_inserted: Mapped[int] = mapped_column(Integer, default=0)
    rows_updated: Mapped[int] = mapped_column(Integer, default=0)
    rows_skipped: Mapped[int] = mapped_column(Integer, default=0)
    # success | partial | failed
    status: Mapped[str] = mapped_column(String(20), default="success")
    error_detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[str | None] = mapped_column(String(100))  # username of importer
