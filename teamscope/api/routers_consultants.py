from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.consultant import Consultant
from app.schemas.consultant import ConsultantCreate, ConsultantUpdate, ConsultantOut
from app.utils.auth import get_current_user

router = APIRouter(prefix="/consultants", tags=["consultants"])
Auth = Annotated[str, Depends(get_current_user)]
DB = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[ConsultantOut])
def list_consultants(db: DB, _: Auth, active_only: bool = False):
    q = db.query(Consultant)
    if active_only:
        q = q.filter(Consultant.is_active == True)
    return q.order_by(Consultant.name).all()


@router.post("", response_model=ConsultantOut, status_code=status.HTTP_201_CREATED)
def create_consultant(body: ConsultantCreate, db: DB, _: Auth):
    consultant = Consultant(**body.model_dump())
    db.add(consultant)
    db.commit()
    db.refresh(consultant)
    return consultant


@router.get("/{consultant_id}", response_model=ConsultantOut)
def get_consultant(consultant_id: int, db: DB, _: Auth):
    c = db.get(Consultant, consultant_id)
    if not c:
        raise HTTPException(status_code=404, detail="Consultant not found")
    return c


@router.patch("/{consultant_id}", response_model=ConsultantOut)
def update_consultant(consultant_id: int, body: ConsultantUpdate, db: DB, _: Auth):
    c = db.get(Consultant, consultant_id)
    if not c:
        raise HTTPException(status_code=404, detail="Consultant not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(c, field, value)
    db.commit()
    db.refresh(c)
    return c


@router.delete("/{consultant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_consultant(consultant_id: int, db: DB, _: Auth):
    c = db.get(Consultant, consultant_id)
    if not c:
        raise HTTPException(status_code=404, detail="Consultant not found")
    db.delete(c)
    db.commit()
