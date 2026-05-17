"""
Pydantic schemas for Assignment and capacity planning operations.

These schemas validate request/response data for the assignment and capacity
grid API endpoints.  They correspond to the following SQLAlchemy models defined
in ``models_assignment.py``:
    - ``Assignment``         (table: ``assignments``)
    - ``WeeklyAllocation``   (table: ``weekly_allocations``)

An Assignment links a consultant to a specific deliverable phase with a date
range and total hours.  When an assignment is saved, the system generates
``WeeklyAllocation`` rows by distributing total_hours evenly across the weeks
in the date range.  These weekly rows drive the capacity grid display and
utilization calculations.

Schema pattern:
    - AssignmentCreate       -- POST /phases/{id}/assignments
    - AssignmentUpdate       -- PATCH /assignments/{id}
    - AssignmentOut          -- Response body (mirrors DB columns)
    - WeeklyAllocationOut    -- Response body for weekly allocation queries
    - GridCell               -- Computed capacity grid cell (not stored in DB)
"""
from datetime import date
from pydantic import BaseModel, Field


class AssignmentCreate(BaseModel):
    """Schema for creating a new assignment (POST /phases/{id}/assignments).

    Links a consultant to a deliverable phase.  The ``consultant_id`` is
    required; dates and hours can be set later via update.

    When saved, the system automatically generates WeeklyAllocation rows
    by distributing total_hours evenly across the weeks between start_date
    and end_date.

    Corresponds to the ``Assignment`` SQLAlchemy model (table: ``assignments``).
    """
    # FK to the consultant performing this assignment; required.
    consultant_id: int
    # Start date of the assignment period; null if not yet scheduled.
    start_date: date | None = None
    # End date of the assignment period; null if not yet scheduled.
    end_date: date | None = None
    # Total hours the consultant is expected to spend; must be >= 0 if provided.
    # Distributed evenly across WeeklyAllocation rows within the date range.
    total_hours: float | None = Field(None, ge=0)
    # Free-form notes (scope clarifications, special instructions); max 500 chars.
    notes: str | None = Field(None, max_length=500)


class AssignmentUpdate(BaseModel):
    """Schema for partially updating an assignment (PATCH /assignments/{id}).

    All fields are optional; only non-None values are applied.
    Changing dates or total_hours triggers a full recalculation of the
    associated WeeklyAllocation rows.

    Corresponds to the ``Assignment`` SQLAlchemy model (table: ``assignments``).
    """
    # Updated consultant FK. None = keep current value.
    consultant_id: int | None = None
    # Updated start date. None = keep current value.
    start_date: date | None = None
    # Updated end date. None = keep current value.
    end_date: date | None = None
    # Updated total hours; must be >= 0 if provided. None = keep current value.
    total_hours: float | None = Field(None, ge=0)
    # Updated notes; max 500 characters. None = keep current value.
    notes: str | None = Field(None, max_length=500)


class AssignmentOut(BaseModel):
    """Response schema for assignment endpoints.

    Mirrors the ``assignments`` table columns.  Includes ``phase_id`` (unlike
    the lightweight AssignmentOut in ``schemas_deliverable.py``) since this
    schema is used in contexts where the phase relationship matters.

    Excludes internal timestamps (created_at, updated_at) and relationship
    objects (phase, consultant, weekly_allocations).

    ``from_attributes = True`` enables direct construction from a SQLAlchemy
    ``Assignment`` ORM instance.
    """
    # Auto-generated primary key.
    id: int
    # FK to the deliverable phase this assignment covers.
    phase_id: int
    # FK to the consultant performing the work.
    consultant_id: int
    # Start date of the assignment period, if set.
    start_date: date | None
    # End date of the assignment period, if set.
    end_date: date | None
    # Total hours budgeted for this assignment, if set.
    total_hours: float | None
    # Free-form notes, if set.
    notes: str | None

    model_config = {"from_attributes": True}


class WeeklyAllocationOut(BaseModel):
    """Response schema for weekly allocation queries.

    Represents a single denormalized row from the ``weekly_allocations`` table,
    showing how many hours a consultant is allocated to a specific project
    during a given week.

    These rows are derived from assignments and are rebuilt on every assignment
    save.  They are the data source for the capacity grid.

    ``from_attributes = True`` enables direct construction from a SQLAlchemy
    ``WeeklyAllocation`` ORM instance.
    """
    # FK to the consultant (denormalized from assignment for query performance).
    consultant_id: int
    # FK to the project (denormalized from assignment -> phase -> deliverable -> project).
    project_id: int
    # Monday of the week this allocation applies to (always a Monday).
    week_start: date
    # Hours allocated to the consultant for this project during this week.
    hours: float

    model_config = {"from_attributes": True}


class GridCell(BaseModel):
    """Single cell in the capacity grid: consultant + week = planned hours.

    This is a computed/aggregated schema that does not directly correspond to
    a single database table.  It aggregates data from ``weekly_allocations``,
    ``assignments``, and ``consultants`` to provide a complete picture of a
    consultant's utilization for a specific week.

    Used by the capacity grid UI to render color-coded cells showing
    utilization levels (green/yellow/red based on threshold settings).
    """
    # The consultant this grid cell represents.
    consultant_id: int
    # The Monday of the week this cell represents.
    week_start: date
    # Total planned (allocated) hours across all projects for this consultant/week.
    planned_hours: float
    # Total actual hours imported from Float for this consultant/week.
    actual_hours: float
    # The consultant's weekly_capacity value (e.g., 40.0 for full-time).
    # Used as the denominator for utilization percentage calculation.
    capacity_hours: float  # consultant.weekly_capacity
    # Utilization percentage: (planned_hours / capacity_hours) * 100.
    # Values > 100 indicate overallocation.
    utilization_pct: float  # planned / capacity * 100
    # Breakdown of hours by project for this consultant/week.
    # Each dict contains: project_id, project_name, color, hours.
    projects: list[dict]   # [{project_id, project_name, color, hours}]
