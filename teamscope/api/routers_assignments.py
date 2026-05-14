"""
Assignment router.
Assignments live under a phase, which lives under a deliverable, which lives under a project.
After every create/update/delete we rebuild the WeeklyAllocation rows for that assignment.
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

router = APIRouter(prefix="/phases", tags=["assignments"])
Auth = Annotated[str, Depends(get_current_user)]
DB = Annotated[Session, Depends(get_db)]


def _get_phase_or_404(db: Session, phase_id: int) -> DeliverablePhase:
    phase = db.query(DeliverablePhase).options(
        selectinload(DeliverablePhase.deliverable)
    ).filter(DeliverablePhase.id == phase_id).first()
    if not phase:
        raise HTTPException(status_code=404, detail="Phase not found")
    return phase


@router.get("/{phase_id}/assignments", response_model=list[AssignmentOut])
def list_assignments(phase_id: int, db: DB, _: Auth):
    _get_phase_or_404(db, phase_id)
    return db.query(Assignment).filter(Assignment.phase_id == phase_id).all()


@router.post("/{phase_id}/assignments", response_model=AssignmentOut, status_code=201)
def create_assignment(phase_id: int, body: AssignmentCreate, db: DB, _: Auth):
    phase = _get_phase_or_404(db, phase_id)
    a = Assignment(phase_id=phase_id, **body.model_dump())
    db.add(a)
    db.flush()
    # Eagerly load relationships needed by rebuild_allocations
    a.phase = phase
    rebuild_allocations(db, a)
    db.commit()
    db.refresh(a)
    return a


@router.patch("/{phase_id}/assignments/{assignment_id}", response_model=AssignmentOut)
def update_assignment(phase_id: int, assignment_id: int, body: AssignmentUpdate, db: DB, _: Auth):
    a = db.query(Assignment).options(
        selectinload(Assignment.phase).selectinload(DeliverablePhase.deliverable)
    ).filter(Assignment.id == assignment_id, Assignment.phase_id == phase_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(a, field, value)
    rebuild_allocations(db, a)
    db.commit()
    db.refresh(a)
    return a


@router.delete("/{phase_id}/assignments/{assignment_id}", status_code=204)
def delete_assignment(phase_id: int, assignment_id: int, db: DB, _: Auth):
    a = db.query(Assignment).filter(
        Assignment.id == assignment_id, Assignment.phase_id == phase_id
    ).first()
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")
    db.delete(a)
    db.commit()
