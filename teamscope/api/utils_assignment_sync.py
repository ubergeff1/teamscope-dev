"""
Auto-sync assignments from deliverable-level fields.

Timeline rules:
  Draft phase  → start_date .. start_date + business_days (business days)
                 If snap_end_to_friday is True on the project, the draft end date
                 snaps forward to the Friday of whichever week it lands in.
  QA phase     → Monday of the week after draft ends .. that Monday + 6 days (one full week)

These are managed assignments — this sync overwrites the first assignment on each phase.
"""
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.assignment import Assignment
from app.models.deliverable import Deliverable
from app.utils.allocation import rebuild_allocations


def _add_business_days(start: date, days: int) -> date:
    """Return the last date of a period of `days` business days starting from `start` inclusive.

    Examples (counting start as day 1):
      Monday + 5  days → Friday of the same week
      Monday + 10 days → Friday of the following week
      Tuesday + 5 days → Monday of the following week
    """
    if days <= 0:
        return start
    current = start
    added = 1  # start date counts as day 1
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:  # Mon–Fri
            added += 1
    return current


def _friday_of_week(d: date) -> date:
    """Return the Friday of the week containing `d`. If d is already Friday, returns d."""
    return d + timedelta(days=(4 - d.weekday()) % 7)


def _next_monday(d: date) -> date:
    """Return the Monday of the week immediately after the week containing `d`."""
    days_since_monday = d.weekday()  # Mon=0 … Sun=6
    current_monday = d - timedelta(days=days_since_monday)
    return current_monday + timedelta(weeks=1)


def _sync_phase_assignment(
    db: Session,
    phase,
    deliverable: Deliverable,
    consultant_id: int | None,
    hours: float | None,
    start: date | None,
    end: date | None,
) -> None:
    """Create or update the single auto-managed assignment on a phase."""
    existing = db.query(Assignment).filter(Assignment.phase_id == phase.id).first()

    if not consultant_id or not hours or not start or not end:
        if existing:
            db.delete(existing)
        return

    if existing:
        existing.consultant_id = consultant_id
        existing.start_date = start
        existing.end_date = end
        existing.total_hours = hours
        existing.phase = phase
        existing.phase.deliverable = deliverable
        rebuild_allocations(db, existing)
    else:
        a = Assignment(
            phase_id=phase.id,
            consultant_id=consultant_id,
            start_date=start,
            end_date=end,
            total_hours=hours,
        )
        db.add(a)
        db.flush()
        a.phase = phase
        a.phase.deliverable = deliverable
        rebuild_allocations(db, a)


def sync_deliverable_assignments(db: Session, deliverable: Deliverable, snap_to_friday: bool = False) -> None:
    """
    Auto-manage assignments for the draft and qa phases.
    Call inside the same transaction after creating/updating a Deliverable,
    with deliverable.phases already loaded.
    snap_to_friday comes from the parent project's snap_end_to_friday field.
    """
    phase_map = {p.phase_type: p for p in deliverable.phases}

    # Resolve consultant hours regardless of deliverable type.
    # flat_hours types store hours directly; control_family/appendix types compute from count × rate.
    if deliverable.flat_hours is not None:
        consultant_hours: float | None = float(deliverable.flat_hours)
    elif deliverable.control_count and deliverable.hours_per_control:
        consultant_hours = float(deliverable.control_count) * float(deliverable.hours_per_control)
    else:
        consultant_hours = None

    # ── Draft phase ───────────────────────────────────────────────────────────
    # Spans start_date → start_date + business_days.
    # If snap_to_friday is on, the end date moves to the Friday of that week.
    draft_end: date | None = None
    draft_phase = phase_map.get("draft")
    if draft_phase:
        if deliverable.start_date and deliverable.consultant_id and consultant_hours:
            draft_start = deliverable.start_date
            draft_end = _add_business_days(draft_start, deliverable.business_days or 5)
            if snap_to_friday:
                draft_end = _friday_of_week(draft_end)
            _sync_phase_assignment(
                db, draft_phase, deliverable,
                consultant_id=deliverable.consultant_id,
                hours=consultant_hours,
                start=draft_start,
                end=draft_end,
            )
        else:
            _sync_phase_assignment(
                db, draft_phase, deliverable,
                consultant_id=None, hours=None, start=None, end=None,
            )

    # ── QA phase ──────────────────────────────────────────────────────────────
    # Always exactly one week, starting the Monday after draft ends.
    # If there is no draft end, estimate it from start_date + business_days.
    qa_phase = phase_map.get("qa")
    if qa_phase:
        if deliverable.qa_consultant_id and deliverable.qa_hours and deliverable.start_date:
            ref_end = draft_end or _add_business_days(
                deliverable.start_date, deliverable.business_days or 5
            )
            if snap_to_friday and not draft_end:
                ref_end = _friday_of_week(ref_end)
            qa_start = _next_monday(ref_end)
            qa_end = qa_start + timedelta(days=6)  # Mon–Sun, one allocation week
            _sync_phase_assignment(
                db, qa_phase, deliverable,
                consultant_id=deliverable.qa_consultant_id,
                hours=float(deliverable.qa_hours),
                start=qa_start,
                end=qa_end,
            )
        else:
            _sync_phase_assignment(
                db, qa_phase, deliverable,
                consultant_id=None, hours=None, start=None, end=None,
            )
