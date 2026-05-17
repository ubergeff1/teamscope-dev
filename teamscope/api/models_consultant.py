"""
Consultant model — represents a team member who can be assigned to deliverables.

This module defines the Consultant entity, which represents an individual
contributor (employee or contractor) in the consulting organization. Consultants
are the resource units for capacity planning — they are assigned to deliverable
phases via assignments and their availability is tracked weekly.

Key fields:
- weekly_capacity: Total available hours per week (default 40), used by the
  capacity grid to calculate utilization percentages.
- float_name: The consultant's name as it appears in Float CSV exports, which
  may differ from the display name (e.g., "J. Smith" vs "John Smith"). Used
  for matching during actual hours import.
- color: Hex color code for visual identification in the capacity grid and
  Gantt charts, ensuring each consultant has a distinct visual identity.
"""
from sqlalchemy import Integer, String, Numeric, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy import DateTime
from app.database import Base


class Consultant(Base):
    """
    A team member available for assignment to project deliverables and workshops.

    Consultants are the core resource in TeamScope's capacity planning system.
    They are assigned to deliverable phases, and their weekly allocations are
    tracked against their weekly_capacity to identify over- or under-utilization.

    Consultants can be linked to projects (via project_consultants), assigned
    to deliverable phases (via assignments), and associated with workshops
    (via workshop_consultants).

    Soft-delete is supported via the is_active flag — inactive consultants
    are excluded from new assignments but their historical data is preserved.
    """
    __tablename__ = "consultants"

    # Primary key — auto-incrementing integer.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Display name of the consultant (e.g., "John Smith").
    # Max 100 characters; required field.
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Email address of the consultant. Must be unique across all consultants.
    # Optional — may not be set for external contractors.
    email: Mapped[str | None] = mapped_column(String(150), unique=True)

    # Maximum available hours per week for this consultant.
    # Defaults to 40.0 (standard full-time). Part-time consultants may have
    # lower values (e.g., 20.0). Used as the denominator when calculating
    # utilization percentage in the capacity grid.
    weekly_capacity: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=40.0)

    # Name as it appears in Float time-tracking CSV exports.
    # May differ from the display name due to formatting differences in Float.
    # Used for fuzzy matching during actual hours import to link Float records
    # to the correct consultant.
    float_name: Mapped[str | None] = mapped_column(String(100))  # Name as it appears in Float CSV

    # Hex color code (e.g., "#4C9BE8") used for visual identification in the
    # capacity grid, Gantt charts, and assignment indicators.
    color: Mapped[str] = mapped_column(String(7), default="#4C9BE8")  # Hex color for grid display

    # Whether this consultant is currently active and available for assignment.
    # Inactive consultants are hidden from assignment dropdowns but their
    # historical assignments and actuals are preserved for reporting.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamp of when this consultant record was first created.
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
