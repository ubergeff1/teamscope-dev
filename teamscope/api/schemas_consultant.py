"""
Pydantic schemas for Consultant CRUD operations.

These schemas validate request/response data for the /consultants API endpoints.
They correspond to the SQLAlchemy ``Consultant`` model defined in
``models_consultant.py`` (table: ``consultants``).

A Consultant represents a team member (employee or contractor) who can be
assigned to deliverable phases and workshops.  Consultants are the resource
units for capacity planning -- their ``weekly_capacity`` sets the denominator
for utilization calculations in the capacity grid.

The ``float_name`` field enables matching against Float time-tracking CSV
exports where the consultant's name may differ from the display name.

Schema pattern:
    - ConsultantCreate  -- POST /consultants  (required fields + defaults)
    - ConsultantUpdate  -- PATCH /consultants/{id}  (all fields optional)
    - ConsultantOut     -- Response body  (mirrors DB columns)
"""
from pydantic import BaseModel, EmailStr, Field


class ConsultantCreate(BaseModel):
    """Schema for creating a new consultant (POST /consultants).

    Only ``name`` is required; other fields have sensible defaults.
    The ``weekly_capacity`` defaults to 40.0 hours (standard full-time),
    ``color`` to the default palette blue, and ``is_active`` to True.

    Corresponds to the ``Consultant`` SQLAlchemy model (table: ``consultants``).
    """
    # Display name of the consultant (e.g., "John Smith"); required, max 100 chars.
    name: str = Field(..., max_length=100)
    # Email address; validated as a proper email format by Pydantic's EmailStr.
    # Optional -- may not be set for external contractors.
    email: EmailStr | None = None
    # Maximum available hours per week. Defaults to 40.0 (full-time).
    # Must be between 0 and 168 (total hours in a week).
    # Used as the denominator for utilization percentage in the capacity grid.
    weekly_capacity: float = Field(40.0, ge=0, le=168)
    # Name as it appears in Float time-tracking CSV exports; max 100 chars.
    # Used for fuzzy matching during actual hours import. Optional.
    float_name: str | None = Field(None, max_length=100)
    # Hex color code for visual identification in grids and charts.
    # Defaults to "#4C9BE8" (palette blue). Must be a valid 6-digit hex color.
    color: str = Field("#4C9BE8", pattern=r"^#[0-9A-Fa-f]{6}$")
    # Whether the consultant is active and available for new assignments.
    # Defaults to True. Set to False for soft-delete (preserves historical data).
    is_active: bool = True


class ConsultantUpdate(BaseModel):
    """Schema for partially updating a consultant (PATCH /consultants/{id}).

    All fields are optional; only non-None values are applied to the existing
    record.

    Corresponds to the ``Consultant`` SQLAlchemy model (table: ``consultants``).
    """
    # Updated display name; max 100 characters. None = keep current value.
    name: str | None = Field(None, max_length=100)
    # Updated email address; validated as EmailStr if provided.
    email: EmailStr | None = None
    # Updated weekly capacity; must be between 0 and 168 if provided.
    weekly_capacity: float | None = Field(None, ge=0, le=168)
    # Updated Float CSV name; max 100 characters. None = keep current value.
    float_name: str | None = Field(None, max_length=100)
    # Updated hex color code; must be a valid 6-digit hex color if provided.
    color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    # Updated active status. None = keep current value.
    is_active: bool | None = None


class ConsultantOut(BaseModel):
    """Response schema for consultant endpoints (GET, POST, PATCH responses).

    Mirrors the ``consultants`` table columns.  Excludes internal timestamps
    (created_at) as they are not needed in the API response.

    Note: ``email`` is typed as ``str | None`` (not ``EmailStr``) because
    output schemas should not re-validate data coming from the database.

    ``from_attributes = True`` enables direct construction from a SQLAlchemy
    ``Consultant`` ORM instance.
    """
    # Auto-generated primary key.
    id: int
    # Display name of the consultant.
    name: str
    # Email address, if set. Typed as plain str for output (no re-validation).
    email: str | None
    # Maximum available hours per week (e.g., 40.0 for full-time).
    weekly_capacity: float
    # Float CSV export name for matching, if set.
    float_name: str | None
    # Hex color code for visual identification.
    color: str
    # Whether the consultant is currently active.
    is_active: bool

    model_config = {"from_attributes": True}
