from datetime import datetime
from pydantic import BaseModel, Field


class ReportConfigCreate(BaseModel):
    name: str = Field(..., max_length=150)
    description: str | None = Field(None, max_length=500)
    report_type: str = Field(
        ...,
        pattern=r"^(capacity_grid|project_summary|actuals_vs_planned|consultant_utilization|deliverable_status)$",
    )
    filters: str | None = None   # JSON string
    columns: str | None = None   # JSON string
    default_format: str = Field("csv", pattern=r"^(csv|excel|pdf)$")
    is_pinned: bool = False


class ReportConfigUpdate(BaseModel):
    name: str | None = Field(None, max_length=150)
    description: str | None = Field(None, max_length=500)
    filters: str | None = None
    columns: str | None = None
    default_format: str | None = Field(None, pattern=r"^(csv|excel|pdf)$")
    is_pinned: bool | None = None


class ReportConfigOut(BaseModel):
    id: int
    name: str
    description: str | None
    report_type: str
    filters: str | None
    columns: str | None
    default_format: str
    is_pinned: bool
    created_by: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
