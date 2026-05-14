"""
Assignment and WeeklyAllocation models.

Assignment: Links a consultant to a deliverable phase with a date range and hours.
  A phase can have multiple assignments (e.g. two consultants splitting work).

WeeklyAllocation: Denormalized per-week rows derived from assignments.
  Recalculated whenever an assignment changes. Used for the capacity grid.
  hours = total_hours spread evenly across working weeks in start_date..end_date.
"""
from sqlalchemy import Integer, String, Numeric, Date, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phase_id: Mapped[int] = mapped_column(ForeignKey("deliverable_phases.id", ondelete="CASCADE"))
    consultant_id: Mapped[int] = mapped_column(ForeignKey("consultants.id", ondelete="CASCADE"))
    start_date: Mapped[Date | None] = mapped_column(Date)
    end_date: Mapped[Date | None] = mapped_column(Date)
    total_hours: Mapped[float | None] = mapped_column(Numeric(6, 2))
    notes: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    phase: Mapped["DeliverablePhase"] = relationship(back_populates="assignments")  # type: ignore
    consultant: Mapped["Consultant"] = relationship("Consultant")  # type: ignore
    weekly_allocations: Mapped[list["WeeklyAllocation"]] = relationship(
        back_populates="assignment", cascade="all, delete-orphan"
    )


class WeeklyAllocation(Base):
    """
    One row per (assignment, week_start). week_start is always Monday.
    hours = assignment.total_hours / number_of_weeks_in_range.
    Rebuilt from scratch when an assignment is saved or deleted.
    """
    __tablename__ = "weekly_allocations"
    __table_args__ = (UniqueConstraint("assignment_id", "week_start"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"))
    consultant_id: Mapped[int] = mapped_column(ForeignKey("consultants.id", ondelete="CASCADE"))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    week_start: Mapped[Date] = mapped_column(Date, nullable=False)  # Monday of the week
    hours: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)

    assignment: Mapped["Assignment"] = relationship(back_populates="weekly_allocations")
