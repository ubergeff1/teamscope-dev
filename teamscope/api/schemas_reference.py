"""
Pydantic schemas for reference/seed data: Frameworks, Impact Levels, and
Control Families.

These schemas provide read-only response models for the /reference API
endpoints.  They correspond to the SQLAlchemy models in
``models_reference.py``:

    - ``Framework``       (table: ``frameworks``)
    - ``ImpactLevel``     (table: ``impact_levels``)
    - ``ControlFamily``   (table: ``control_families``)

This data is pre-populated by ``database/init/01_seed.sql`` and is read-only
in the application.  There are no Create or Update schemas because these
records are managed via database migrations, not the API.

The hierarchy is:  Framework -> Impact Levels -> Control Families.
For example:  FedRAMP -> Moderate -> [AC, AU, CA, CM, ...] with each control
family having a known control_count.

These schemas are used when:
  - Populating framework/impact-level dropdowns in the project creation UI
  - Displaying available control families for a selected impact level
  - Providing control_count defaults when creating control_family-type deliverables
"""
from pydantic import BaseModel


class ControlFamilyOut(BaseModel):
    """Response schema for a single control family.

    A control family (e.g. "AC - Access Control") belongs to a specific
    impact level and has a fixed number of controls.  The ``control_count``
    is used to calculate total hours for control_family-type deliverables
    (control_count * hours_per_control).

    Corresponds to the ``ControlFamily`` SQLAlchemy model
    (table: ``control_families``).
    """
    # Auto-generated primary key.
    id: int
    # Short code identifying the family (e.g. "AC", "AU", "CA", "CM").
    # Unique within an impact level.
    code: str
    # Full display name (e.g. "Access Control", "Audit and Accountability").
    name: str
    # Number of individual controls in this family; used for hour calculations.
    control_count: int

    model_config = {"from_attributes": True}


class ImpactLevelOut(BaseModel):
    """Response schema for an impact level within a framework.

    An impact level (e.g. "Low", "Moderate", "High" for FedRAMP, or
    "L1", "L2", "L3" for CMMC) determines which control families are
    in scope for a project.

    Nests a list of ``ControlFamilyOut`` objects representing all control
    families applicable at this impact level.

    Corresponds to the ``ImpactLevel`` SQLAlchemy model
    (table: ``impact_levels``).
    """
    # Auto-generated primary key.
    id: int
    # Impact level name (e.g. "Low", "Moderate", "High", "L1", "L2", "L3").
    name: str
    # Control families available at this impact level.
    # Populated via the SQLAlchemy relationship; defaults to empty list.
    control_families: list[ControlFamilyOut] = []

    model_config = {"from_attributes": True}


class FrameworkOut(BaseModel):
    """Response schema for a compliance framework.

    A framework (e.g. "FedRAMP", "GovRAMP", "CMMC") is the top-level
    organizational unit for compliance standards.  Each framework contains
    one or more impact levels, which in turn contain control families.

    Nests a list of ``ImpactLevelOut`` objects.  Used by the frontend to
    build cascading dropdowns: select framework -> select impact level ->
    view available control families.

    Corresponds to the ``Framework`` SQLAlchemy model (table: ``frameworks``).
    """
    # Auto-generated primary key.
    id: int
    # Framework name (e.g. "FedRAMP", "GovRAMP", "CMMC"). Unique in the database.
    name: str
    # Optional description of the framework.
    description: str | None
    # Impact levels belonging to this framework, each with nested control families.
    impact_levels: list[ImpactLevelOut] = []

    model_config = {"from_attributes": True}
