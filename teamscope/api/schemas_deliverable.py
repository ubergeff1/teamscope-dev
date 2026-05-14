from datetime import date
from pydantic import BaseModel, Field

_DELIVERABLE_STATUS = r"^(not_started|in_progress|in_qa|delivered|complete)$"
_DELIVERABLE_TYPE   = r"^(control_family|appendix|workshop|flat_hours|custom)$"
_WORKSHOP_STATUS    = r"^(scheduled|prep_in_progress|completed|cancelled)$"


# ── DeliverablePhase ──────────────────────────────────────────────────────────

class AssignmentOut(BaseModel):
    id: int
    consultant_id: int
    start_date: date | None
    end_date: date | None
    total_hours: float | None
    notes: str | None

    model_config = {"from_attributes": True}


class PhaseOut(BaseModel):
    id: int
    phase_type: str
    start_date: date | None
    end_date: date | None
    total_hours: float | None
    status: str
    sort_order: int
    assignments: list[AssignmentOut] = []

    model_config = {"from_attributes": True}


class PhaseUpdate(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    total_hours: float | None = Field(None, ge=0)
    status: str | None = Field(None, pattern=_DELIVERABLE_STATUS)


# ── Deliverable ───────────────────────────────────────────────────────────────

class DeliverableCreate(BaseModel):
    name: str = Field(..., max_length=200)
    deliverable_type: str = Field("custom", pattern=_DELIVERABLE_TYPE)
    control_family_id: int | None = None
    control_count: int | None = Field(None, ge=0)
    hours_per_control: float | None = Field(None, ge=0)
    flat_hours: float | None = Field(None, ge=0)
    qa_hours: float | None = Field(None, ge=0)
    business_days: int | None = Field(None, ge=0)
    qa_business_days: int | None = Field(None, ge=0)
    workshop_sequential: bool = False
    qa_sequential: bool = False
    start_date: date | None = None
    end_date: date | None = None
    workshop_id: int | None = None
    consultant_id: int | None = None
    qa_consultant_id: int | None = None
    status: str = Field("not_started", pattern=_DELIVERABLE_STATUS)
    sort_order: int = 0


class DeliverableUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    deliverable_type: str | None = Field(None, pattern=_DELIVERABLE_TYPE)
    control_family_id: int | None = None
    control_count: int | None = Field(None, ge=0)
    hours_per_control: float | None = Field(None, ge=0)
    flat_hours: float | None = Field(None, ge=0)
    qa_hours: float | None = Field(None, ge=0)
    business_days: int | None = Field(None, ge=0)
    qa_business_days: int | None = Field(None, ge=0)
    workshop_sequential: bool | None = None
    qa_sequential: bool | None = None
    start_date: date | None = None
    end_date: date | None = None
    draft_start_date: date | None = None
    draft_end_date: date | None = None
    qa_start_date: date | None = None
    qa_end_date: date | None = None
    workshop_id: int | None = None
    consultant_id: int | None = None
    qa_consultant_id: int | None = None
    status: str | None = Field(None, pattern=_DELIVERABLE_STATUS)
    sort_order: int | None = None


class DeliverableOut(BaseModel):
    id: int
    project_id: int
    name: str
    deliverable_type: str
    control_family_id: int | None
    control_count: int | None
    hours_per_control: float | None
    flat_hours: float | None
    qa_hours: float | None
    business_days: int | None
    qa_business_days: int | None
    workshop_sequential: bool
    qa_sequential: bool
    start_date: date | None
    end_date: date | None
    workshop_id: int | None
    consultant_id: int | None
    qa_consultant_id: int | None
    status: str
    sort_order: int
    total_planned_hours: float
    phases: list[PhaseOut] = []

    model_config = {"from_attributes": True}


# ── Workshop ──────────────────────────────────────────────────────────────────

class WorkshopConsultantOut(BaseModel):
    id: int
    name: str
    color: str
    is_active: bool
    model_config = {"from_attributes": True}


class WorkshopCreate(BaseModel):
    name: str = Field(..., max_length=200)
    workshop_date: date | None = None
    status: str = Field("scheduled", pattern=_WORKSHOP_STATUS)
    consultant_ids: list[int] = []
    duration_hours: float | None = Field(None, ge=0)


class WorkshopUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    workshop_date: date | None = None
    status: str | None = Field(None, pattern=_WORKSHOP_STATUS)
    consultant_ids: list[int] | None = None
    duration_hours: float | None = Field(None, ge=0)


class WorkshopOut(BaseModel):
    id: int
    project_id: int
    name: str
    workshop_date: date | None
    status: str
    duration_hours: float | None = None
    consultants: list[WorkshopConsultantOut] = []

    model_config = {"from_attributes": True}


class DeliverableReorder(BaseModel):
    ids: list[int]
