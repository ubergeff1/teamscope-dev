"""
Frameworks router — API prefix: /frameworks

Provides read-only access to compliance frameworks and their hierarchical
structure. Frameworks (e.g., CMMC, NIST 800-171) contain impact levels,
which in turn contain control families with their control counts.

This data is used by the template system to resolve control_family_code
references and calculate hours for control-family-type deliverables.

Endpoints:
  GET /frameworks — List all frameworks with their impact levels and control families
"""
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.reference import Framework, ImpactLevel, ControlFamily
from app.schemas.reference import FrameworkOut, ImpactLevelOut, ControlFamilyOut
from app.utils.auth import get_current_user

# Router setup: all endpoints prefixed with /frameworks, grouped under "frameworks" tag
router = APIRouter(prefix="/frameworks", tags=["frameworks"])
# Type aliases for dependency injection
Auth = Annotated[str, Depends(get_current_user)]
DB = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[FrameworkOut])
def list_frameworks(db: DB, _: Auth):
    """GET /frameworks — List all compliance frameworks with full hierarchy.

    Eagerly loads the complete framework tree in a single query:
      Framework -> ImpactLevel -> ControlFamily

    This avoids N+1 queries when the response is serialized. The frontend
    uses this data to populate framework/impact-level/control-family dropdowns
    when configuring projects and templates.

    Returns frameworks ordered alphabetically by name.
    """
    return (
        db.query(Framework)
        .options(
            # Eagerly load two levels deep: impact_levels and their control_families
            selectinload(Framework.impact_levels).selectinload(ImpactLevel.control_families)
        )
        .order_by(Framework.name)
        .all()
    )
