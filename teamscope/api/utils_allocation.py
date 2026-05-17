"""
Weekly allocation calculation.

When an Assignment is saved (created or updated), this module rebuilds its
WeeklyAllocation rows. WeeklyAllocation is the fundamental unit used by the
capacity grid and reports -- it answers the question "how many hours does
consultant X spend on project Y during the week starting Monday Z?"

Allocation algorithm:
  1. Identify all Mondays that fall within the assignment's [start_date, end_date]
     range (inclusive on both ends). Each Monday represents one allocation week.
  2. Divide the assignment's total_hours evenly across those weeks.
  3. Create one WeeklyAllocation row per week.

Example: An assignment of 40 hours spanning 4 weeks produces 4 WeeklyAllocation
rows of 10 hours each. Hours are rounded to 2 decimal places to avoid floating-
point display issues.

If start_date, end_date, or total_hours is None/falsy, no allocations are created
(any existing ones are deleted).

Design notes:
  - This is a full rebuild (delete-then-recreate), not a differential update.
    This keeps the logic simple and avoids edge cases when date ranges change.
  - The function must be called inside the same DB transaction as the assignment
    save so that allocations are always consistent with their parent assignment.
  - The project_id on WeeklyAllocation is denormalized (it could be derived via
    assignment -> phase -> deliverable -> project) for query performance in the
    capacity grid, which needs to aggregate hours by consultant and project.
"""
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.assignment import Assignment, WeeklyAllocation


def _mondays_between(start: date, end: date) -> list[date]:
    """Return a list of all Monday dates in the inclusive range [start, end].

    Algorithm:
      1. Find the first Monday on or after ``start`` using modular arithmetic.
         ``(7 - start.weekday()) % 7`` gives the number of days until the next
         Monday; if ``start`` is already Monday (weekday=0), this yields 0.
      2. Step forward in 7-day increments, collecting each Monday, until we
         pass ``end``.

    Parameters:
        start: The beginning of the date range (inclusive).
        end:   The end of the date range (inclusive).

    Returns:
        A list of ``datetime.date`` objects, each a Monday, sorted chronologically.
        Returns an empty list if no Monday falls within the range (e.g., a
        single-day range on a Wednesday).
    """
    # Advance to the first Monday on or after start
    days_ahead = (7 - start.weekday()) % 7  # weekday(): Mon=0
    first_monday = start + timedelta(days=days_ahead)
    mondays = []
    current = first_monday
    while current <= end:
        mondays.append(current)
        current += timedelta(weeks=1)
    return mondays


def rebuild_allocations(db: Session, assignment: Assignment) -> None:
    """
    Delete existing WeeklyAllocation rows for this assignment, then recreate them
    with hours spread evenly across the weeks in the assignment's date range.

    This function is called inside the same transaction as the assignment save
    (from utils_assignment_sync.py or from the assignments router when a user
    manually edits an assignment).

    Steps:
      1. Delete all existing WeeklyAllocation rows for this assignment ID.
      2. If any required field is missing (start_date, end_date, total_hours),
         return early -- the assignment has no allocatable period.
      3. Compute the list of Mondays in [start_date, end_date].
      4. Divide total_hours evenly across those Mondays (rounded to 2 decimals).
      5. Look up project_id by traversing assignment -> phase -> deliverable.
      6. Create one WeeklyAllocation row per Monday.

    Parameters:
        db:         Active SQLAlchemy session (within a transaction).
        assignment: The Assignment ORM object whose allocations should be rebuilt.
                    Must have ``.phase.deliverable`` relationships accessible
                    (either eagerly loaded or set explicitly by the caller).
    """
    # Step 1: Delete old allocation rows (full rebuild strategy)
    db.query(WeeklyAllocation).filter(
        WeeklyAllocation.assignment_id == assignment.id
    ).delete()

    # Step 2: Guard -- nothing to allocate if dates or hours are missing
    if not assignment.start_date or not assignment.end_date or not assignment.total_hours:
        return

    # Step 3: Find all Mondays (week boundaries) within the assignment window
    mondays = _mondays_between(assignment.start_date, assignment.end_date)
    if not mondays:
        return

    # Step 4: Spread hours evenly across weeks, rounded to 2 decimal places
    hours_per_week = round(float(assignment.total_hours) / len(mondays), 2)

    # Step 5: Retrieve project_id via the phase -> deliverable relationship chain.
    # This is denormalized onto WeeklyAllocation for efficient grid queries.
    phase = assignment.phase
    deliverable = phase.deliverable
    project_id = deliverable.project_id

    # Step 6: Create one allocation row per week
    for monday in mondays:
        alloc = WeeklyAllocation(
            assignment_id=assignment.id,
            consultant_id=assignment.consultant_id,
            project_id=project_id,
            week_start=monday,
            hours=hours_per_week,
        )
        db.add(alloc)
