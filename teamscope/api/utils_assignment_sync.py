"""
Auto-sync assignments from deliverable-level fields.

This module implements "managed assignments" -- assignments that are automatically
created, updated, or deleted whenever a Deliverable's fields change. The goal is
to keep the assignment timeline in sync with high-level deliverable metadata
(consultant, hours, start date, business days) so users do not need to manually
create or adjust assignments when editing a deliverable.

Timeline rules (how dates are computed):
  Draft phase  -> start_date .. start_date + business_days (business days only)
                  If snap_end_to_friday is True on the parent project, the draft
                  end date is pushed forward to the Friday of whichever ISO week
                  the computed end date falls in. This is useful for aligning
                  deliverable boundaries to weekly reporting cadences.
  QA phase     -> Starts on the Monday immediately following the draft end date
                  (i.e., the next full work week). The QA window is always exactly
                  one calendar week: Monday through Sunday (7 days).

Key design decisions:
  - Each phase may have at most ONE auto-managed assignment. If the user has not
    provided the required fields (consultant, hours, start date), any existing
    managed assignment is deleted rather than left stale.
  - After creating or updating an assignment, ``rebuild_allocations`` is called to
    recompute the weekly hour breakdown (see utils_allocation.py).
  - This function is meant to be called inside the same DB transaction that
    modifies the deliverable, so all changes commit or roll back atomically.
"""
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.assignment import Assignment
from app.models.deliverable import Deliverable
from app.utils.allocation import rebuild_allocations


def _add_business_days(start: date, days: int) -> date:
    """Return the last date of a period of ``days`` business days starting from ``start`` inclusive.

    Algorithm:
      1. The start date itself counts as business day 1 (inclusive counting).
      2. We step forward one calendar day at a time, incrementing the counter
         only on weekdays (Monday=0 through Friday=4).
      3. We stop when we have accumulated ``days`` business days and return the
         current calendar date.

    This means the result is the *last working day* of the period, not the day
    after it. For example, 5 business days starting Monday yields Friday of the
    same week (Mon=1, Tue=2, Wed=3, Thu=4, Fri=5).

    Parameters:
        start: The first day of the period (counts as day 1).
        days:  Number of business days in the period. If <= 0, ``start`` is
               returned unchanged.

    Returns:
        The calendar date of the last business day in the period.

    Examples (counting start as day 1):
      Monday + 5  days -> Friday of the same week
      Monday + 10 days -> Friday of the following week
      Tuesday + 5 days -> Monday of the following week (skips weekend)
    """
    if days <= 0:
        return start
    current = start
    added = 1  # start date counts as day 1
    while added < days:
        current += timedelta(days=1)
        # Only count weekdays (Mon=0 .. Fri=4); skip Sat=5 and Sun=6
        if current.weekday() < 5:  # Mon-Fri
            added += 1
    return current


def _friday_of_week(d: date) -> date:
    """Return the Friday of the ISO week containing ``d``.

    Uses modular arithmetic: Friday is weekday 4 (Mon=0). The expression
    ``(4 - d.weekday()) % 7`` gives the number of days to add to reach Friday.
    If ``d`` is already Friday the result is 0, so ``d`` itself is returned.
    If ``d`` is Saturday (5) or Sunday (6), this rolls *forward* to the next
    Friday -- but in practice those dates should not occur because
    ``_add_business_days`` never lands on a weekend.

    Parameters:
        d: Any calendar date.

    Returns:
        The Friday (weekday 4) of the same ISO week, or the next Friday if ``d``
        is on a weekend.
    """
    return d + timedelta(days=(4 - d.weekday()) % 7)


def _next_monday(d: date) -> date:
    """Return the Monday of the week immediately after the week containing ``d``.

    Algorithm:
      1. Find the Monday of ``d``'s week by subtracting ``d.weekday()`` days
         (weekday() returns 0 for Monday, so subtracting 0 keeps Monday as-is).
      2. Add exactly 7 days to jump to the following Monday.

    This is used to position the QA phase: QA always starts on the Monday after
    the draft phase ends, regardless of which day of the week draft ends on.

    Parameters:
        d: Any calendar date (typically the draft phase end date).

    Returns:
        The Monday of the next ISO week.
    """
    days_since_monday = d.weekday()  # Mon=0 ... Sun=6
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
    """Create, update, or delete the single auto-managed assignment on a phase.

    This is the core upsert/delete logic for managed assignments. Each phase
    (draft or QA) has at most one auto-managed assignment. The behavior depends
    on whether the required fields are present:

      - If ANY of consultant_id, hours, start, or end is missing (None/0/falsy):
        delete the existing assignment if one exists, then return. This handles
        the case where a user clears a field on the deliverable.
      - If all fields are present AND an assignment already exists: update the
        existing row in place, then rebuild its weekly allocations.
      - If all fields are present AND no assignment exists: create a new
        Assignment row, flush to get its auto-generated ID, then rebuild
        allocations.

    The ``phase`` and ``deliverable`` relationships are explicitly set on the
    assignment object so that ``rebuild_allocations`` can traverse
    assignment -> phase -> deliverable -> project_id without requiring an
    additional DB query.

    Parameters:
        db:            Active SQLAlchemy session (within a transaction).
        phase:         The Phase ORM object (draft or QA) to attach the assignment to.
        deliverable:   The parent Deliverable ORM object (used to set relationships).
        consultant_id: ID of the assigned consultant, or None to clear.
        hours:         Total hours for the assignment, or None to clear.
        start:         Assignment start date, or None to clear.
        end:           Assignment end date, or None to clear.
    """
    # Look for an existing managed assignment on this phase
    existing = db.query(Assignment).filter(Assignment.phase_id == phase.id).first()

    # If any required field is missing, remove the assignment entirely
    if not consultant_id or not hours or not start or not end:
        if existing:
            db.delete(existing)
        return

    if existing:
        # Update the existing assignment in place
        existing.consultant_id = consultant_id
        existing.start_date = start
        existing.end_date = end
        existing.total_hours = hours
        # Attach relationships so rebuild_allocations can navigate the ORM graph
        existing.phase = phase
        existing.phase.deliverable = deliverable
        rebuild_allocations(db, existing)
    else:
        # Create a brand-new assignment
        a = Assignment(
            phase_id=phase.id,
            consultant_id=consultant_id,
            start_date=start,
            end_date=end,
            total_hours=hours,
        )
        db.add(a)
        # Flush to generate the assignment's primary key (needed by rebuild_allocations)
        db.flush()
        # Attach relationships for allocation rebuild
        a.phase = phase
        a.phase.deliverable = deliverable
        rebuild_allocations(db, a)


def sync_deliverable_assignments(db: Session, deliverable: Deliverable, snap_to_friday: bool = False) -> None:
    """
    Auto-manage assignments for the draft and QA phases of a deliverable.

    This is the main public entry point of the module. It should be called inside
    the same database transaction after creating or updating a Deliverable, with
    ``deliverable.phases`` already eagerly loaded.

    The overall algorithm:
      1. Build a lookup map of phase_type -> Phase object.
      2. Compute total consultant hours from the deliverable's fields. Two
         strategies exist:
           a. ``flat_hours``: The deliverable stores a single hours value directly.
           b. ``control_count * hours_per_control``: Used for control-family or
              appendix-type deliverables where effort scales with the number of
              controls.
         If neither is available, hours are None and assignments will be cleared.
      3. Sync the draft-phase assignment (consultant doing the primary work).
      4. Sync the QA-phase assignment (QA reviewer, separate consultant).

    Parameters:
        db:              Active SQLAlchemy session (within a transaction).
        deliverable:     The Deliverable ORM object, with ``.phases`` loaded.
        snap_to_friday:  If True, the draft end date is snapped forward to the
                         Friday of its week. This flag comes from the parent
                         project's ``snap_end_to_friday`` setting and is used to
                         align deliverable timelines to weekly boundaries.
    """
    # Build a quick lookup so we can find draft/qa phases by name
    phase_map = {p.phase_type: p for p in deliverable.phases}

    # ── Step 1: Resolve total consultant hours ────────────────────────────────
    # Two calculation strategies depending on the deliverable type:
    #   - flat_hours: directly specified (e.g., "this deliverable takes 40 hours")
    #   - control_count * hours_per_control: computed (e.g., 20 controls x 2 hrs each = 40 hrs)
    # If neither is available, consultant_hours will be None, which causes
    # downstream _sync_phase_assignment calls to delete any existing assignment.
    if deliverable.flat_hours is not None:
        consultant_hours: float | None = float(deliverable.flat_hours)
    elif deliverable.control_count and deliverable.hours_per_control:
        consultant_hours = float(deliverable.control_count) * float(deliverable.hours_per_control)
    else:
        consultant_hours = None

    # ── Step 2: Draft phase ───────────────────────────────────────────────────
    # The draft phase represents the primary work period. Its timeline:
    #   start = deliverable.start_date
    #   end   = start + business_days (defaults to 5 if not specified)
    # If snap_to_friday is enabled, the end date is pushed to Friday of that week
    # so that the draft always ends on a week boundary.
    draft_end: date | None = None
    draft_phase = phase_map.get("draft")
    if draft_phase:
        if deliverable.start_date and deliverable.consultant_id and consultant_hours:
            draft_start = deliverable.start_date
            # Default to 5 business days (one work week) if not explicitly set
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
            # Missing required fields -- clear any existing draft assignment
            _sync_phase_assignment(
                db, draft_phase, deliverable,
                consultant_id=None, hours=None, start=None, end=None,
            )

    # ── Step 3: QA phase ──────────────────────────────────────────────────────
    # The QA phase is always exactly one calendar week (Mon-Sun), starting the
    # Monday after the draft phase ends. This ensures there is no overlap and
    # the QA reviewer gets a clean week to review.
    #
    # If draft_end was not computed (e.g., the draft phase does not exist), we
    # estimate a reference end date using the same business-day calculation so
    # that QA still gets a reasonable start date.
    qa_phase = phase_map.get("qa")
    if qa_phase:
        if deliverable.qa_consultant_id and deliverable.qa_hours and deliverable.start_date:
            # Use draft_end if available; otherwise compute a reference end date
            ref_end = draft_end or _add_business_days(
                deliverable.start_date, deliverable.business_days or 5
            )
            # Apply snap_to_friday to the reference date only if we had to compute
            # it ourselves (draft_end already has the snap applied if applicable)
            if snap_to_friday and not draft_end:
                ref_end = _friday_of_week(ref_end)
            qa_start = _next_monday(ref_end)
            qa_end = qa_start + timedelta(days=6)  # Mon-Sun, one full allocation week
            _sync_phase_assignment(
                db, qa_phase, deliverable,
                consultant_id=deliverable.qa_consultant_id,
                hours=float(deliverable.qa_hours),
                start=qa_start,
                end=qa_end,
            )
        else:
            # Missing required QA fields -- clear any existing QA assignment
            _sync_phase_assignment(
                db, qa_phase, deliverable,
                consultant_id=None, hours=None, start=None, end=None,
            )
