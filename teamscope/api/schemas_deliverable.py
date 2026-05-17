"""
Pydantic schemas for Deliverable, DeliverablePhase, and Workshop CRUD operations.

These schemas validate request/response data for the /projects/{id}/deliverables,
/deliverables/{id}/phases, and /projects/{id}/workshops API endpoints.

They correspond to the following SQLAlchemy models defined in
``models_deliverable.py``:
    - ``Deliverable``       (table: ``deliverables``)
    - ``DeliverablePhase``  (table: ``deliverable_phases``)
    - ``Workshop``          (table: ``workshops``)

Deliverables are the primary work items within a project.  Each deliverable
progresses through up to 4 phases (workshop, draft, qa, delivery), each with
its own date range, hour allocation, and consultant assignments.

Workshops are scheduled interactive sessions (e.g., kickoff meetings, control
walkthroughs) that can be linked to deliverables as phase dependencies.

Schema pattern per entity:
    - *Create  -- POST endpoint  (required fields + defaults)
    - *Update  -- PATCH endpoint (all fields optional for partial updates)
    - *Out     -- Response body  (mirrors DB columns, may include nested children)

Additional schemas:
    - DeliverableReorder -- PUT endpoint for bulk sort-order updates
"""
from datetime import date
from pydantic import BaseModel, Field

# Regex patterns for status/type validation, shared across Create/Update schemas.
# Deliverable status lifecycle: not_started -> in_progress -> in_qa -> delivered -> complete
_DELIVERABLE_STATUS = r"^(not_started|in_progress|in_qa|delivered|complete)$"
# Deliverable type determines hour-calculation formula and UI behavior.
_DELIVERABLE_TYPE   = r"^(control_family|appendix|workshop|flat_hours|custom)$"
# Workshop status lifecycle: scheduled -> prep_in_progress -> completed -> cancelled
_WORKSHOP_STATUS    = r"^(scheduled|prep_in_progress|completed|cancelled)$"


# ── DeliverablePhase ──────────────────────────────────────────────────────────

class AssignmentOut(BaseModel):
    """Lightweight assignment summary nested within PhaseOut responses.

    Contains the essential fields needed to display consultant assignments
    on the deliverable detail view.  This is a local schema used only within
    this module for nesting -- the full AssignmentOut with phase_id lives
    in ``schemas_assignment.py``.

    Corresponds to the ``Assignment`` SQLAlchemy model (table: ``assignments``).
    """
    # Auto-generated primary key of the assignment.
    id: int
    # FK to the consultant performing this assignment.
    consultant_id: int
    # Start date of the assignment period; null if not yet scheduled.
    start_date: date | None
    # End date of the assignment period; null if not yet scheduled.
    end_date: date | None
    # Total hours the consultant is expected to spend; null if not yet estimated.
    total_hours: float | None
    # Free-form notes about the assignment.
    notes: str | None

    # Enable construction from SQLAlchemy ORM instances.
    model_config = {"from_attributes": True}


class PhaseOut(BaseModel):
    """Response schema for a single deliverable phase.

    Each deliverable can have up to 4 phases (workshop, draft, qa, delivery),
    each independently tracked with its own dates, hours, status, and
    consultant assignments.

    Corresponds to the ``DeliverablePhase`` SQLAlchemy model
    (table: ``deliverable_phases``).
    """
    # Auto-generated primary key.
    id: int
    # Phase type/stage: workshop | draft | qa | delivery.
    phase_type: str
    # Planned or actual start date for this phase; null if not yet scheduled.
    start_date: date | None
    # Planned or actual end date for this phase; null if not yet scheduled.
    end_date: date | None
    # Total hours allocated to this phase; null if not yet estimated.
    total_hours: float | None
    # Current status of the phase (uses same values as deliverable status).
    status: str
    # Display ordering within the parent deliverable (workshop=0, draft=1, qa=2, delivery=3).
    sort_order: int
    # Consultant assignments for this phase; empty list if no one is assigned yet.
    assignments: list[AssignmentOut] = []

    # Enable construction from SQLAlchemy ORM instances.
    model_config = {"from_attributes": True}


class PhaseUpdate(BaseModel):
    """Schema for partially updating a deliverable phase
    (PATCH /deliverables/{id}/phases/{phase_id}).

    All fields are optional; only non-None values are applied.
    Phase type and sort_order are not updatable after creation.
    """
    # Updated start date for the phase. None = keep current value.
    start_date: date | None = None
    # Updated end date for the phase. None = keep current value.
    end_date: date | None = None
    # Updated total hours; must be >= 0 if provided. None = keep current value.
    total_hours: float | None = Field(None, ge=0)
    # Updated phase status; must match deliverable status pattern if provided.
    status: str | None = Field(None, pattern=_DELIVERABLE_STATUS)


# ── Deliverable ───────────────────────────────────────────────────────────────

class DeliverableCreate(BaseModel):
    """Schema for creating a new deliverable (POST /projects/{id}/deliverables).

    Only ``name`` is strictly required; other fields have sensible defaults.
    The ``deliverable_type`` defaults to "custom" and ``status`` to "not_started".

    Hour-calculation fields depend on deliverable_type:
    - control_family: uses control_count * hours_per_control
    - flat_hours / appendix / custom: uses flat_hours directly
    - workshop: hours derived from linked workshop duration

    Corresponds to the ``Deliverable`` SQLAlchemy model (table: ``deliverables``).
    """
    # Display name of the deliverable; required, max 200 characters.
    name: str = Field(..., max_length=200)
    # Type determining hour-calculation formula. Defaults to "custom".
    # Valid values: control_family | appendix | workshop | flat_hours | custom
    deliverable_type: str = Field("custom", pattern=_DELIVERABLE_TYPE)
    # FK to the control family from reference data. Only used for control_family type.
    control_family_id: int | None = None
    # Number of controls in the family; must be >= 0. Used with hours_per_control.
    control_count: int | None = Field(None, ge=0)
    # Hours budgeted per individual control; must be >= 0.
    hours_per_control: float | None = Field(None, ge=0)
    # Fixed consultant hours for flat_hours/appendix/custom types; must be >= 0.
    flat_hours: float | None = Field(None, ge=0)
    # Hours allocated for QA/review; must be >= 0.
    qa_hours: float | None = Field(None, ge=0)
    # Business days for the drafting phase; used by auto-scheduler. Must be >= 0.
    business_days: int | None = Field(None, ge=0)
    # Business days for the QA phase; used by auto-scheduler. Must be >= 0.
    qa_business_days: int | None = Field(None, ge=0)
    # If True, workshop phase must complete before draft phase begins.
    workshop_sequential: bool = False
    # If True, QA phase starts only after draft phase completes.
    qa_sequential: bool = False
    # Planned start date; may be auto-calculated by the scheduler.
    start_date: date | None = None
    # Planned end date; may be auto-calculated from start_date + business_days.
    end_date: date | None = None
    # FK to an associated workshop for phase dependency.
    workshop_id: int | None = None
    # FK to the primary consultant assigned to draft this deliverable.
    consultant_id: int | None = None
    # FK to the consultant assigned to QA/review.
    qa_consultant_id: int | None = None
    # Initial lifecycle status. Defaults to "not_started".
    status: str = Field("not_started", pattern=_DELIVERABLE_STATUS)
    # Display order within the project. Lower values appear first.
    sort_order: int = 0


class DeliverableUpdate(BaseModel):
    """Schema for partially updating a deliverable
    (PATCH /projects/{id}/deliverables/{deliverable_id}).

    All fields are optional; only non-None values are applied.
    Includes additional date fields (draft_start_date, draft_end_date,
    qa_start_date, qa_end_date) for directly updating phase dates.

    Corresponds to the ``Deliverable`` SQLAlchemy model (table: ``deliverables``).
    """
    # Updated display name; max 200 characters. None = keep current value.
    name: str | None = Field(None, max_length=200)
    # Updated deliverable type. None = keep current value.
    deliverable_type: str | None = Field(None, pattern=_DELIVERABLE_TYPE)
    # Updated control family FK. None = keep current value.
    control_family_id: int | None = None
    # Updated control count; must be >= 0 if provided.
    control_count: int | None = Field(None, ge=0)
    # Updated hours per control; must be >= 0 if provided.
    hours_per_control: float | None = Field(None, ge=0)
    # Updated flat consultant hours; must be >= 0 if provided.
    flat_hours: float | None = Field(None, ge=0)
    # Updated QA hours; must be >= 0 if provided.
    qa_hours: float | None = Field(None, ge=0)
    # Updated business days for drafting phase; must be >= 0 if provided.
    business_days: int | None = Field(None, ge=0)
    # Updated QA business days; must be >= 0 if provided.
    qa_business_days: int | None = Field(None, ge=0)
    # Updated workshop-sequential flag. None = keep current value.
    workshop_sequential: bool | None = None
    # Updated QA-sequential flag. None = keep current value.
    qa_sequential: bool | None = None
    # Updated overall deliverable start date. None = keep current value.
    start_date: date | None = None
    # Updated overall deliverable end date. None = keep current value.
    end_date: date | None = None
    # Updated draft phase start date (convenience shortcut). None = keep current value.
    draft_start_date: date | None = None
    # Updated draft phase end date (convenience shortcut). None = keep current value.
    draft_end_date: date | None = None
    # Updated QA phase start date (convenience shortcut). None = keep current value.
    qa_start_date: date | None = None
    # Updated QA phase end date (convenience shortcut). None = keep current value.
    qa_end_date: date | None = None
    # Updated workshop FK. None = keep current value.
    workshop_id: int | None = None
    # Updated primary consultant FK. None = keep current value.
    consultant_id: int | None = None
    # Updated QA consultant FK. None = keep current value.
    qa_consultant_id: int | None = None
    # Updated lifecycle status. None = keep current value.
    status: str | None = Field(None, pattern=_DELIVERABLE_STATUS)
    # Updated display order. None = keep current value.
    sort_order: int | None = None


class DeliverableOut(BaseModel):
    """Response schema for deliverable endpoints.

    Mirrors the ``deliverables`` table columns plus a computed
    ``total_planned_hours`` property (flat_hours + qa_hours) and a nested
    list of ``PhaseOut`` objects representing the deliverable's phases.

    Excludes internal fields (monday_item_id, created_at, updated_at)
    and relationship objects (project, control_family) for response size.

    ``from_attributes = True`` enables direct construction from a SQLAlchemy
    ``Deliverable`` ORM instance.
    """
    # Auto-generated primary key.
    id: int
    # FK to the parent project.
    project_id: int
    # Display name of the deliverable.
    name: str
    # Deliverable type: control_family | appendix | workshop | flat_hours | custom.
    deliverable_type: str
    # FK to the control family from reference data, if applicable.
    control_family_id: int | None
    # Number of controls for control_family type deliverables.
    control_count: int | None
    # Hours per control for control_family type deliverables.
    hours_per_control: float | None
    # Fixed consultant hours for flat_hours/appendix/custom types.
    flat_hours: float | None
    # Hours allocated for QA/review.
    qa_hours: float | None
    # Business days for the drafting phase.
    business_days: int | None
    # Business days for the QA phase.
    qa_business_days: int | None
    # Whether workshop must complete before draft begins.
    workshop_sequential: bool
    # Whether QA starts only after draft completes.
    qa_sequential: bool
    # Planned start date, if set.
    start_date: date | None
    # Planned end date, if set.
    end_date: date | None
    # FK to the associated workshop, if set.
    workshop_id: int | None
    # FK to the primary drafting consultant, if assigned.
    consultant_id: int | None
    # FK to the QA consultant, if assigned.
    qa_consultant_id: int | None
    # Current lifecycle status.
    status: str
    # Display order within the project.
    sort_order: int
    # Computed property: flat_hours + qa_hours (treats None as 0).
    total_planned_hours: float
    # Ordered list of phases (workshop, draft, qa, delivery) with nested assignments.
    phases: list[PhaseOut] = []

    model_config = {"from_attributes": True}


# ── Workshop ──────────────────────────────────────────────────────────────────

class WorkshopConsultantOut(BaseModel):
    """Lightweight consultant summary for embedding in workshop responses.

    Contains the fields needed to display consultant badges on the workshop
    detail view.  Similar to ``ConsultantBrief`` in ``schemas_project.py``
    but defined locally for workshop-specific nesting.

    Corresponds to a subset of the ``Consultant`` SQLAlchemy model
    (table: ``consultants``).
    """
    # Auto-generated primary key of the consultant.
    id: int
    # Display name of the consultant.
    name: str
    # Hex color code for visual identification.
    color: str
    # Whether the consultant is currently active.
    is_active: bool
    model_config = {"from_attributes": True}


class WorkshopCreate(BaseModel):
    """Schema for creating a new workshop (POST /projects/{id}/workshops).

    Only ``name`` is required.  The ``status`` defaults to "scheduled" and
    ``workshop_date`` can be set later when the meeting is confirmed.

    Corresponds to the ``Workshop`` SQLAlchemy model (table: ``workshops``).
    """
    # Display name of the workshop (e.g., "Kickoff Meeting"); required, max 200 chars.
    name: str = Field(..., max_length=200)
    # Scheduled date for the workshop session; null if not yet scheduled.
    workshop_date: date | None = None
    # Lifecycle status. Defaults to "scheduled".
    # Valid values: scheduled | prep_in_progress | completed | cancelled
    status: str = Field("scheduled", pattern=_WORKSHOP_STATUS)
    # List of consultant IDs to assign to this workshop via the join table.
    consultant_ids: list[int] = []
    # Expected duration of the session in hours; must be >= 0 if provided.
    duration_hours: float | None = Field(None, ge=0)


class WorkshopUpdate(BaseModel):
    """Schema for partially updating a workshop
    (PATCH /projects/{id}/workshops/{workshop_id}).

    All fields are optional; only non-None values are applied.

    Corresponds to the ``Workshop`` SQLAlchemy model (table: ``workshops``).
    """
    # Updated workshop name; max 200 characters. None = keep current value.
    name: str | None = Field(None, max_length=200)
    # Updated scheduled date. None = keep current value.
    workshop_date: date | None = None
    # Updated lifecycle status; must match workshop status pattern if provided.
    status: str | None = Field(None, pattern=_WORKSHOP_STATUS)
    # Updated list of consultant IDs; replaces current assignments entirely.
    # None = keep current assignments unchanged.
    consultant_ids: list[int] | None = None
    # Updated duration in hours; must be >= 0 if provided. None = keep current value.
    duration_hours: float | None = Field(None, ge=0)


class WorkshopOut(BaseModel):
    """Response schema for workshop endpoints.

    Mirrors the ``workshops`` table columns plus a nested list of
    ``WorkshopConsultantOut`` objects representing the assigned consultants.

    Excludes internal fields (monday_item_id, created_at).

    ``from_attributes = True`` enables direct construction from a SQLAlchemy
    ``Workshop`` ORM instance.
    """
    # Auto-generated primary key.
    id: int
    # FK to the parent project.
    project_id: int
    # Display name of the workshop.
    name: str
    # Scheduled date for the session, if set.
    workshop_date: date | None
    # Current lifecycle status: scheduled | prep_in_progress | completed | cancelled.
    status: str
    # Duration of the workshop in hours, if set.
    duration_hours: float | None = None
    # Consultants assigned to this workshop (lightweight summaries).
    consultants: list[WorkshopConsultantOut] = []

    model_config = {"from_attributes": True}


class DeliverableReorder(BaseModel):
    """Schema for bulk-reordering deliverables within a project
    (PUT /projects/{id}/deliverables/reorder).

    Accepts an ordered list of deliverable IDs.  The position in the list
    determines the new sort_order value (index 0 = sort_order 0, etc.).
    All deliverable IDs for the project must be included.
    """
    # Ordered list of deliverable IDs defining the new display sequence.
    ids: list[int]
