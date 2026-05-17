"""
Assignment and WeeklyAllocation models.

This module defines the resource allocation layer of TeamScope:

Assignment: Links a consultant to a specific deliverable phase with a date range
  and total hours. A single phase can have multiple assignments when work is split
  between consultants (e.g., two people sharing a 40-hour drafting task).

WeeklyAllocation: Denormalized per-week rows derived from assignments. These rows
  are the backbone of the capacity grid — they represent how many hours a consultant
  is allocated to a specific project in a given week.

  Recalculation: Weekly allocations are rebuilt from scratch whenever an assignment
  is created, updated, or deleted. The hours are spread evenly across the working
  weeks that fall within the assignment's start_date..end_date range.

  Example: An assignment of 40 hours spanning 4 weeks produces 4 WeeklyAllocation
  rows of 10 hours each.
"""
from sqlalchemy import Integer, String, Numeric, Date, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base


class Assignment(Base):
    """
    Maps a consultant to a deliverable phase with a time range and hour budget.

    Assignments are the primary mechanism for allocating consultant time to work.
    Each assignment specifies who (consultant_id), what (phase_id), when
    (start_date..end_date), and how much (total_hours).

    When an assignment is saved, the system automatically generates WeeklyAllocation
    rows by distributing total_hours evenly across the weeks in the date range.
    These weekly rows drive the capacity grid display and utilization calculations.

    Multiple assignments per phase are supported for split-work scenarios.
    """
    __tablename__ = "assignments"

    # Primary key — auto-incrementing integer.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # FK to the deliverable phase this assignment covers.
    # CASCADE delete ensures assignments are removed when their phase is deleted.
    phase_id: Mapped[int] = mapped_column(ForeignKey("deliverable_phases.id", ondelete="CASCADE"))

    # FK to the consultant performing this assignment.
    # CASCADE delete ensures assignments are removed when the consultant is deleted.
    consultant_id: Mapped[int] = mapped_column(ForeignKey("consultants.id", ondelete="CASCADE"))

    # Start date of the assignment period. Used to determine which weeks
    # receive allocated hours. Should be a Monday for clean week boundaries,
    # but the system handles mid-week starts gracefully.
    start_date: Mapped[Date | None] = mapped_column(Date)

    # End date of the assignment period. The last week containing this date
    # will receive allocated hours.
    end_date: Mapped[Date | None] = mapped_column(Date)

    # Total hours the consultant is expected to spend on this phase.
    # Distributed evenly across WeeklyAllocation rows spanning start_date to end_date.
    # Precision: up to 9,999.99 hours.
    total_hours: Mapped[float | None] = mapped_column(Numeric(6, 2))

    # Free-form notes about this assignment (e.g., special instructions,
    # scope clarifications). Max 500 characters.
    notes: Mapped[str | None] = mapped_column(String(500))

    # Timestamp of when this assignment was first created.
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Timestamp of the last modification, auto-updated on every UPDATE.
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # --- Relationships ---

    # The deliverable phase this assignment belongs to.
    phase: Mapped["DeliverablePhase"] = relationship(back_populates="assignments")  # type: ignore

    # The consultant performing the work for this assignment.
    consultant: Mapped["Consultant"] = relationship("Consultant")  # type: ignore

    # Derived weekly hour breakdowns for this assignment.
    # Cascade delete ensures allocations are removed when the assignment is deleted.
    # These rows are rebuilt from scratch on every assignment save.
    weekly_allocations: Mapped[list["WeeklyAllocation"]] = relationship(
        back_populates="assignment", cascade="all, delete-orphan"
    )


class WeeklyAllocation(Base):
    """
    Denormalized per-week hour allocation derived from an assignment.

    One row per (assignment, week_start) pair. week_start is always a Monday,
    ensuring consistent week boundaries across the entire system.

    Hours are calculated as: assignment.total_hours / number_of_weeks_in_range.
    These rows are rebuilt from scratch whenever an assignment is saved or deleted,
    so they should be treated as computed/derived data.

    The denormalized consultant_id and project_id fields are included to enable
    efficient capacity grid queries without requiring joins back through the
    assignment -> phase -> deliverable -> project chain.
    """
    __tablename__ = "weekly_allocations"

    # Unique constraint ensures only one allocation row exists per assignment
    # per week. Prevents duplicate entries during recalculation.
    __table_args__ = (UniqueConstraint("assignment_id", "week_start"),)

    # Primary key — auto-incrementing integer.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # FK to the parent assignment this allocation was derived from.
    # CASCADE delete ensures allocations are cleaned up with their assignment.
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"))

    # Denormalized FK to the consultant. Copied from the parent assignment
    # to enable direct capacity grid queries without multi-table joins.
    # CASCADE delete for referential integrity.
    consultant_id: Mapped[int] = mapped_column(ForeignKey("consultants.id", ondelete="CASCADE"))

    # Denormalized FK to the project. Derived from assignment -> phase ->
    # deliverable -> project. Stored directly for query performance in the
    # capacity grid, which groups allocations by consultant and project per week.
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))

    # The Monday of the week this allocation applies to. Always a Monday
    # to ensure consistent week boundaries across the system.
    week_start: Mapped[Date] = mapped_column(Date, nullable=False)  # Monday of the week

    # Hours allocated to the consultant for this project during this week.
    # Calculated as assignment.total_hours / number_of_weeks_in_assignment_range.
    hours: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)

    # --- Relationships ---

    # Back-reference to the parent assignment.
    assignment: Mapped["Assignment"] = relationship(back_populates="weekly_allocations")
