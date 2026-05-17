"""
Pydantic schemas for Project CRUD operations.

These schemas validate request/response data for the /projects API endpoints.
They correspond to the SQLAlchemy ``Project`` model defined in
``models_project.py`` (table: ``projects``).

A Project is the top-level organizational unit in TeamScope, representing a
client consulting engagement governed by a compliance framework (e.g., FedRAMP,
CMMC) at a particular impact level.  Projects contain deliverables, workshops,
and are linked to consultants via the ``project_consultants`` join table.

Schema pattern:
    - ConsultantBrief     -- Lightweight consultant summary nested in ProjectOut
    - ProjectCreate       -- POST /projects  (required fields + defaults)
    - ProjectUpdate       -- PATCH /projects/{id}  (all fields optional)
    - ProjectOut          -- Response body  (mirrors DB columns + nested consultants)
"""
from datetime import date
from pydantic import BaseModel, Field


class ConsultantBrief(BaseModel):
    """Lightweight consultant summary for embedding in project responses.

    Contains only the fields needed for display in the project detail view
    (e.g., consultant badges/chips showing who is assigned to a project).
    This avoids returning full consultant records with every project query.

    Corresponds to a subset of the ``Consultant`` SQLAlchemy model
    (table: ``consultants``).
    """
    # Auto-generated primary key of the consultant.
    id: int
    # Display name of the consultant (e.g., "John Smith").
    name: str
    # Hex color code (e.g., "#4C9BE8") for visual identification in the UI.
    color: str
    # Whether the consultant is currently active and available for assignment.
    is_active: bool

    # Enable construction from SQLAlchemy ORM instances via .model_validate().
    model_config = {"from_attributes": True}


class ProjectCreate(BaseModel):
    """Schema for creating a new project (POST /projects).

    Only ``name`` is strictly required; all other fields have sensible defaults.
    The ``status`` defaults to "active" and ``color`` is pre-set to the default
    palette blue.  Framework and impact level can be assigned later via update.

    Corresponds to the ``Project`` SQLAlchemy model (table: ``projects``).
    """
    # Display name of the project; required, max 200 characters.
    name: str = Field(..., max_length=200)
    # Name of the client organization; optional, max 200 characters.
    client_name: str | None = Field(None, max_length=200)
    # FK to the compliance framework (e.g., FedRAMP, CMMC). Optional.
    framework_id: int | None = None
    # FK to the impact level within the framework (e.g., Low, Moderate, High). Optional.
    impact_level_id: int | None = None
    # Planned engagement start date. Optional; used for timeline views.
    start_date: date | None = None
    # Planned engagement end date. May be snapped to Friday if snap_end_to_friday is True.
    end_date: date | None = None
    # Lifecycle status of the project. Must be one of: active, on_hold, complete, archived.
    # Defaults to "active" for new projects.
    status: str = Field("active", pattern=r"^(active|on_hold|complete|archived)$")
    # External Monday.com project ID for import/sync delta-matching. Optional; max 100 chars.
    monday_project_id: str | None = Field(None, max_length=100)
    # Hex color code for visual identification in grids and charts.
    # Defaults to "#4C9BE8" (palette blue). Must be a valid 6-digit hex color.
    color: str = Field("#4C9BE8", pattern=r"^#[0-9A-Fa-f]{6}$")
    # Free-form notes about the project (assumptions, special instructions, etc.).
    notes: str | None = None
    # Total contracted hours for the engagement; used for budget variance tracking.
    budgeted_hours: float | None = None
    # When True, the auto-scheduler aligns the project end date to the nearest Friday.
    snap_end_to_friday: bool = False


class ProjectUpdate(BaseModel):
    """Schema for partially updating a project (PATCH /projects/{id}).

    All fields are optional; only non-None values are applied to the existing
    record.  This enables partial updates where the client sends only the
    fields that changed.

    Corresponds to the ``Project`` SQLAlchemy model (table: ``projects``).
    """
    # Updated project name; max 200 characters. None = keep current value.
    name: str | None = Field(None, max_length=200)
    # Updated client organization name. None = keep current value.
    client_name: str | None = Field(None, max_length=200)
    # Updated framework FK. None = keep current value.
    framework_id: int | None = None
    # Updated impact level FK. None = keep current value.
    impact_level_id: int | None = None
    # Updated start date. None = keep current value.
    start_date: date | None = None
    # Updated end date. None = keep current value.
    end_date: date | None = None
    # Updated lifecycle status; must be one of: active, on_hold, complete, archived.
    status: str | None = Field(None, pattern=r"^(active|on_hold|complete|archived)$")
    # Updated Monday.com project ID. None = keep current value.
    monday_project_id: str | None = Field(None, max_length=100)
    # Updated hex color code; must be a valid 6-digit hex color if provided.
    color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    # Updated free-form notes. None = keep current value.
    notes: str | None = None
    # Updated budgeted hours. None = keep current value.
    budgeted_hours: float | None = None
    # Updated snap-to-Friday flag. None = keep current value.
    snap_end_to_friday: bool | None = None


class ProjectOut(BaseModel):
    """Response schema for project endpoints (GET, POST, PATCH responses).

    Mirrors the ``projects`` table columns plus a nested list of
    ``ConsultantBrief`` objects representing the consultants assigned to
    the project via the ``project_consultants`` join table.

    Excludes internal timestamps (created_at, updated_at) and relationship
    objects (framework, impact_level, deliverables, workshops) to keep
    the response lightweight.  Use dedicated sub-resource endpoints for
    those details.

    ``from_attributes = True`` enables direct construction from a SQLAlchemy
    ``Project`` ORM instance.
    """
    # Auto-generated primary key.
    id: int
    # Project display name.
    name: str
    # Client organization name, if set.
    client_name: str | None
    # FK to the compliance framework, if set.
    framework_id: int | None
    # FK to the impact level, if set.
    impact_level_id: int | None
    # Planned start date, if set.
    start_date: date | None
    # Planned end date, if set.
    end_date: date | None
    # Current lifecycle status: active | on_hold | complete | archived.
    status: str
    # Monday.com project ID for sync, if set.
    monday_project_id: str | None
    # Hex color code for visual identification.
    color: str
    # Free-form notes, if set.
    notes: str | None
    # Total contracted hours for budget tracking, if set.
    budgeted_hours: float | None
    # Whether end dates are snapped to Fridays by the auto-scheduler.
    snap_end_to_friday: bool
    # Consultants assigned to this project (lightweight summaries).
    # Populated from the project_consultants join table via SQLAlchemy relationship.
    consultants: list[ConsultantBrief] = []

    model_config = {"from_attributes": True}
