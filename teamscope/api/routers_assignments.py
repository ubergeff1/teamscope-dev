"""
Assignment router — API prefix: /phases

Manages assignments within deliverable phases. Assignments represent the
allocation of a consultant to work on a specific phase of a deliverable.

The resource hierarchy is:
  Project -> Deliverable -> Phase -> Assignment -> WeeklyAllocation

After every create/update/delete, the WeeklyAllocation rows for the affected
assignment are rebuilt to keep the capacity grid data in sync.

Endpoints:
  GET    /phases/{phase_id}/assignments                  — List assignments for a phase
  POST   /phases/{phase_id}/assignments                  — Create an assignment
  PATCH  /phases/{phase_id}/assignments/{assignment_id}  — Update an assignment
  DELETE /phases/{phase_id}/assignments/{assignment_id}  — Delete an assignment
"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.assignment import Assignment
from app.models.deliverable import DeliverablePhase, Deliverable
from app.schemas.assignment import AssignmentCreate, AssignmentUpdate, AssignmentOut
from app.utils.auth import get_current_user
from app.utils.allocation import rebuild_allocations

# Router setup: endpoints are prefixed with /phases (assignments are a sub-resource of phases)
router = APIRouter(prefix="/phases", tags=["assignments"])
# Type aliases for dependency injection
Auth = Annotated[str, Depends(get_current_user)]
DB = Annotated[Session, Depends(get_db)]


def _get_phase_or_404(db: Session, phase_id: int) -> DeliverablePhase:
    """Fetch a deliverable phase by ID with its parent deliverable eagerly loaded.

    The deliverable relationship is needed by rebuild_allocations to access
    project-level settings (e.g., snap_end_to_friday). Returns 404 if not found.
    """
    phase = db.query(DeliverablePhase).options(
        selectinload(DeliverablePhase.deliverable)
    ).filter(DeliverablePhase.id == phase_id).first()
    if not phase:
        raise HTTPException(status_code=404, detail="Phase not found")
    return phase


@router.get("/{phase_id}/assignments", response_model=list[AssignmentOut])
def list_assignments(phase_id: int, db: DB, _: Auth):
    """GET /phases/{phase_id}/assignments — List all assignments for a phase.

    Validates that the phase exists before querying assignments.
    Returns all assignments belonging to the specified phase.
    """
    _get_phase_or_404(db, phase_id)
    return db.query(Assignment).filter(Assignment.phase_id == phase_id).all()


@router.post("/{phase_id}/assignments", response_model=AssignmentOut, status_code=201)
def create_assignment(phase_id: int, body: AssignmentCreate, db: DB, _: Auth):
    """POST /phases/{phase_id}/assignments — Create a new assignment.

    Creates an assignment linking a consultant to a phase with allocated hours.
    After creation:
    1. Flushes to get the assignment ID
    2. Eagerly sets the phase relationship for rebuild_allocations
    3. Rebuilds WeeklyAllocation rows to distribute hours across weeks
    """
    phase = _get_phase_or_404(db, phase_id)
    a = Assignment(phase_id=phase_id, **body.model_dump())
    db.add(a)
    db.flush()  # Get the assignment ID before rebuilding allocations
    # Eagerly load the phase relationship needed by rebuild_allocations
    a.phase = phase
    # Rebuild WeeklyAllocation rows to distribute hours across the phase's date range
    rebuild_allocations(db, a)
    db.commit()
    db.refresh(a)
    return a


@router.patch("/{phase_id}/assignments/{assignment_id}", response_model=AssignmentOut)
def update_assignment(phase_id: int, assignment_id: int, body: AssignmentUpdate, db: DB, _: Auth):
    """PATCH /phases/{phase_id}/assignments/{assignment_id} — Partially update an assignment.

    Updates the assignment fields and then rebuilds WeeklyAllocation rows
    to reflect changes in hours, consultant, or date range. Eagerly loads
    the full phase -> deliverable chain needed by the allocation rebuild.
    """
    # Eagerly load the full relationship chain for rebuild_allocations
    a = db.query(Assignment).options(
        selectinload(Assignment.phase).selectinload(DeliverablePhase.deliverable)
    ).filter(Assignment.id == assignment_id, Assignment.phase_id == phase_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")
    # Apply only the fields that were explicitly sent
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(a, field, value)
    # Rebuild allocations to reflect the updated assignment data
    rebuild_allocations(db, a)
    db.commit()
    db.refresh(a)
    return a


@router.delete("/{phase_id}/assignments/{assignment_id}", status_code=204)
def delete_assignment(phase_id: int, assignment_id: int, db: DB, _: Auth):
    """DELETE /phases/{phase_id}/assignments/{assignment_id} — Delete an assignment.

    Removes the assignment and its associated WeeklyAllocation rows
    (handled by cascading deletes). Returns 204 No Content on success.
    """
    a = db.query(Assignment).filter(
        Assignment.id == assignment_id, Assignment.phase_id == phase_id
    ).first()
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")
    db.delete(a)
    db.commit()
