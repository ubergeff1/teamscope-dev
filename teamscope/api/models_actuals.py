"""
Actual hours and import log models.

This module defines the time-tracking and import audit layer of TeamScope:

Actual: Records the hours a consultant actually charged to a project in a given
  week. These are typically imported from Float CSV exports via a silent upsert
  (no approval workflow). Actuals are compared against WeeklyAllocations to
  calculate variance (planned vs. actual) in reports and dashboards.

  The week_start field is always normalized to Monday to match the WeeklyAllocation
  convention, ensuring consistent joins between planned and actual data.

ImportLog: Provides an audit trail for every data import operation (Float CSVs,
  Monday.com syncs, etc.). Records the source, timestamp, row counts, and any
  errors encountered during the import process. Useful for debugging import
  issues and tracking data provenance.
"""
from sqlalchemy import Integer, String, Text, Numeric, Date, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base


class Actual(Base):
    """
    Actual hours charged by a consultant to a project in a specific week.

    Represents real time-tracking data imported from external systems (primarily
    Float). Each row captures the total hours a consultant worked on a project
    during a given week (Monday to Friday).

    The unique constraint on (consultant_id, project_id, week_start) ensures
    only one record exists per consultant-project-week combination. Subsequent
    imports for the same combination will upsert (update the existing record).

    Actuals are compared against WeeklyAllocation records to calculate:
    - Budget variance (are we over or under planned hours?)
    - Utilization accuracy (how well did we estimate?)
    """
    __tablename__ = "actuals"

    # Unique constraint ensures one record per consultant-project-week combination.
    # Import logic uses this for upsert behavior — if a matching row exists,
    # it updates the hours rather than inserting a duplicate.
    __table_args__ = (UniqueConstraint("consultant_id", "project_id", "week_start"),)

    # Primary key — auto-incrementing integer.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # FK to the consultant who logged these hours.
    # CASCADE delete ensures actuals are removed when the consultant is deleted.
    consultant_id: Mapped[int] = mapped_column(ForeignKey("consultants.id", ondelete="CASCADE"))

    # FK to the project these hours were charged to.
    # CASCADE delete ensures actuals are removed when the project is deleted.
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))

    # The Monday of the week these hours apply to. Always normalized to Monday
    # for consistent alignment with WeeklyAllocation records.
    week_start: Mapped[Date] = mapped_column(Date, nullable=False)  # Monday of the week

    # Total hours actually worked during this week. Precision: up to 9,999.99.
    hours: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)

    # Source system that provided this actual hours record.
    # Valid values: float | manual
    # "float" indicates data imported from Float CSV; "manual" indicates
    # hand-entered data via the UI.
    source: Mapped[str] = mapped_column(String(20), default="float")  # float | manual

    # Timestamp of when this actual hours record was first created.
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Timestamp of the last modification, auto-updated on every UPDATE.
    # Tracks when an import last refreshed this record.
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # --- Relationships ---

    # The consultant who logged these hours.
    consultant: Mapped["Consultant"] = relationship("Consultant")  # type: ignore

    # The project these hours were charged to.
    project: Mapped["Project"] = relationship("Project")  # type: ignore


class ImportLog(Base):
    """
    Audit trail record for a data import operation.

    Each import — whether a Float CSV upload, Monday.com sync, or delta import —
    creates one ImportLog row capturing the outcome. This provides traceability
    for data provenance and helps diagnose import failures.

    The status field indicates the overall outcome:
    - success: All rows processed without errors
    - partial: Some rows succeeded, some failed (see error_detail)
    - failed: The entire import failed (see error_detail)
    """
    __tablename__ = "import_logs"

    # Primary key — auto-incrementing integer.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Identifies the type/source of the import operation.
    # Valid values: float_actuals | monday_projects | monday_delta
    source: Mapped[str] = mapped_column(String(30), nullable=False)

    # Original filename of the imported file (e.g., "float_export_2025_01.csv").
    # Null for API-based imports (e.g., Monday.com sync) that don't involve a file.
    filename: Mapped[str | None] = mapped_column(String(255))

    # Total number of rows/records read from the source data.
    rows_processed: Mapped[int] = mapped_column(Integer, default=0)

    # Number of new records inserted into the database.
    rows_inserted: Mapped[int] = mapped_column(Integer, default=0)

    # Number of existing records updated (upserted) with new data.
    rows_updated: Mapped[int] = mapped_column(Integer, default=0)

    # Number of rows skipped (e.g., due to missing consultant match,
    # invalid data, or duplicate detection).
    rows_skipped: Mapped[int] = mapped_column(Integer, default=0)

    # Overall outcome of the import operation.
    # Valid values: success | partial | failed
    status: Mapped[str] = mapped_column(String(20), default="success")

    # Detailed error information when status is "partial" or "failed".
    # May contain stack traces, row-level error messages, or validation details.
    error_detail: Mapped[str | None] = mapped_column(Text)

    # Timestamp of when this import was executed.
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Username or identifier of the person who initiated the import.
    # Null for automated/scheduled imports.
    created_by: Mapped[str | None] = mapped_column(String(100))  # username of importer
