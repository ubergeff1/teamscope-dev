"""
Weekly allocation calculation.

When an Assignment is saved, this module rebuilds its WeeklyAllocation rows.
Hours are spread evenly across the Mondays that fall within [start_date, end_date].

Example: 40 hours over 4 weeks → 10 hours/week.
If start_date or end_date is None, no allocations are created.
"""
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.assignment import Assignment, WeeklyAllocation


def _mondays_between(start: date, end: date) -> list[date]:
    """Return list of Mondays in [start, end] inclusive."""
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
    Delete existing WeeklyAllocation rows for this assignment, then recreate them.
    Called inside the same transaction as the assignment save.
    """
    # Delete old rows
    db.query(WeeklyAllocation).filter(
        WeeklyAllocation.assignment_id == assignment.id
    ).delete()

    if not assignment.start_date or not assignment.end_date or not assignment.total_hours:
        return

    mondays = _mondays_between(assignment.start_date, assignment.end_date)
    if not mondays:
        return

    hours_per_week = round(float(assignment.total_hours) / len(mondays), 2)

    # Retrieve project_id via the phase → deliverable relationship
    phase = assignment.phase
    deliverable = phase.deliverable
    project_id = deliverable.project_id

    for monday in mondays:
        alloc = WeeklyAllocation(
            assignment_id=assignment.id,
            consultant_id=assignment.consultant_id,
            project_id=project_id,
            week_start=monday,
            hours=hours_per_week,
        )
        db.add(alloc)
