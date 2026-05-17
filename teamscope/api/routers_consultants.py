"""
Consultants router — API prefix: /consultants

Provides full CRUD operations for managing consultant records. Consultants
represent team members who are assigned to projects and deliverables.

Endpoints:
  GET    /consultants              — List all consultants (optionally active-only)
  POST   /consultants              — Create a new consultant
  GET    /consultants/{id}         — Retrieve a single consultant
  PATCH  /consultants/{id}         — Partially update a consultant
  DELETE /consultants/{id}         — Delete a consultant
"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.consultant import Consultant
from app.schemas.consultant import ConsultantCreate, ConsultantUpdate, ConsultantOut
from app.utils.auth import get_current_user

# Router setup: all endpoints prefixed with /consultants, grouped under "consultants" tag
router = APIRouter(prefix="/consultants", tags=["consultants"])
# Type aliases for dependency injection — used in all endpoint signatures
Auth = Annotated[str, Depends(get_current_user)]
DB = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[ConsultantOut])
def list_consultants(db: DB, _: Auth, active_only: bool = False):
    """GET /consultants — List all consultants.

    Query params:
      active_only (optional, default False): if True, only return consultants
        where is_active is True. Useful for filtering out archived consultants.
    Returns consultants ordered alphabetically by name.
    """
    q = db.query(Consultant)
    if active_only:
        q = q.filter(Consultant.is_active == True)
    return q.order_by(Consultant.name).all()


@router.post("", response_model=ConsultantOut, status_code=status.HTTP_201_CREATED)
def create_consultant(body: ConsultantCreate, db: DB, _: Auth):
    """POST /consultants — Create a new consultant.

    Accepts consultant fields (name, email, weekly_capacity, color, etc.)
    in the request body. Returns the created consultant with its generated ID.
    """
    consultant = Consultant(**body.model_dump())
    db.add(consultant)
    db.commit()
    db.refresh(consultant)
    return consultant


@router.get("/{consultant_id}", response_model=ConsultantOut)
def get_consultant(consultant_id: int, db: DB, _: Auth):
    """GET /consultants/{consultant_id} — Retrieve a single consultant by ID.

    Returns 404 if the consultant does not exist.
    """
    c = db.get(Consultant, consultant_id)
    if not c:
        raise HTTPException(status_code=404, detail="Consultant not found")
    return c


@router.patch("/{consultant_id}", response_model=ConsultantOut)
def update_consultant(consultant_id: int, body: ConsultantUpdate, db: DB, _: Auth):
    """PATCH /consultants/{consultant_id} — Partially update a consultant.

    Only fields included in the request body are updated (exclude_unset=True).
    Returns the updated consultant. Returns 404 if not found.
    """
    c = db.get(Consultant, consultant_id)
    if not c:
        raise HTTPException(status_code=404, detail="Consultant not found")
    # Apply only the fields that were explicitly sent in the request
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(c, field, value)
    db.commit()
    db.refresh(c)
    return c


@router.delete("/{consultant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_consultant(consultant_id: int, db: DB, _: Auth):
    """DELETE /consultants/{consultant_id} — Delete a consultant.

    Permanently removes the consultant record. Cascading deletes are handled
    by database foreign key constraints. Returns 204 No Content on success.
    """
    c = db.get(Consultant, consultant_id)
    if not c:
        raise HTTPException(status_code=404, detail="Consultant not found")
    db.delete(c)
    db.commit()
