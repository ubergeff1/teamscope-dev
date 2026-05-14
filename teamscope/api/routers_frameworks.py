from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.reference import Framework, ImpactLevel, ControlFamily
from app.schemas.reference import FrameworkOut, ImpactLevelOut, ControlFamilyOut
from app.utils.auth import get_current_user

router = APIRouter(prefix="/frameworks", tags=["frameworks"])
Auth = Annotated[str, Depends(get_current_user)]
DB = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[FrameworkOut])
def list_frameworks(db: DB, _: Auth):
    return (
        db.query(Framework)
        .options(
            selectinload(Framework.impact_levels).selectinload(ImpactLevel.control_families)
        )
        .order_by(Framework.name)
        .all()
    )
