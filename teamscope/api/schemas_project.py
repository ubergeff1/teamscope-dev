from datetime import date
from pydantic import BaseModel, Field


class ConsultantBrief(BaseModel):
    id: int
    name: str
    color: str
    is_active: bool

    model_config = {"from_attributes": True}


class ProjectCreate(BaseModel):
    name: str = Field(..., max_length=200)
    client_name: str | None = Field(None, max_length=200)
    framework_id: int | None = None
    impact_level_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: str = Field("active", pattern=r"^(active|on_hold|complete|archived)$")
    monday_project_id: str | None = Field(None, max_length=100)
    color: str = Field("#4C9BE8", pattern=r"^#[0-9A-Fa-f]{6}$")
    notes: str | None = None
    budgeted_hours: float | None = None
    snap_end_to_friday: bool = False


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    client_name: str | None = Field(None, max_length=200)
    framework_id: int | None = None
    impact_level_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = Field(None, pattern=r"^(active|on_hold|complete|archived)$")
    monday_project_id: str | None = Field(None, max_length=100)
    color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    notes: str | None = None
    budgeted_hours: float | None = None
    snap_end_to_friday: bool | None = None


class ProjectOut(BaseModel):
    id: int
    name: str
    client_name: str | None
    framework_id: int | None
    impact_level_id: int | None
    start_date: date | None
    end_date: date | None
    status: str
    monday_project_id: str | None
    color: str
    notes: str | None
    budgeted_hours: float | None
    snap_end_to_friday: bool
    consultants: list[ConsultantBrief] = []

    model_config = {"from_attributes": True}
