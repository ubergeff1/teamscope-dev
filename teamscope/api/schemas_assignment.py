from datetime import date
from pydantic import BaseModel, Field


class AssignmentCreate(BaseModel):
    consultant_id: int
    start_date: date | None = None
    end_date: date | None = None
    total_hours: float | None = Field(None, ge=0)
    notes: str | None = Field(None, max_length=500)


class AssignmentUpdate(BaseModel):
    consultant_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    total_hours: float | None = Field(None, ge=0)
    notes: str | None = Field(None, max_length=500)


class AssignmentOut(BaseModel):
    id: int
    phase_id: int
    consultant_id: int
    start_date: date | None
    end_date: date | None
    total_hours: float | None
    notes: str | None

    model_config = {"from_attributes": True}


class WeeklyAllocationOut(BaseModel):
    consultant_id: int
    project_id: int
    week_start: date
    hours: float

    model_config = {"from_attributes": True}


class GridCell(BaseModel):
    """Single cell in the capacity grid: consultant + week = planned hours."""
    consultant_id: int
    week_start: date
    planned_hours: float
    actual_hours: float
    capacity_hours: float  # consultant.weekly_capacity
    utilization_pct: float  # planned / capacity * 100
    projects: list[dict]   # [{project_id, project_name, color, hours}]
