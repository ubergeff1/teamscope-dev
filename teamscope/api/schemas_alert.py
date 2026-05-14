from datetime import datetime
from pydantic import BaseModel, Field


class AlertRuleCreate(BaseModel):
    name: str = Field(..., max_length=150)
    rule_type: str = Field(
        ..., pattern=r"^(overallocation|underallocation|budget_threshold|unassigned_deliverable|custom)$"
    )
    rule_config: str | None = None  # JSON string
    is_active: bool = True


class AlertRuleUpdate(BaseModel):
    name: str | None = Field(None, max_length=150)
    rule_type: str | None = None
    rule_config: str | None = None
    is_active: bool | None = None


class AlertRuleOut(BaseModel):
    id: int
    name: str
    rule_type: str
    rule_config: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class AlertInstanceOut(BaseModel):
    id: int
    rule_id: int
    consultant_id: int | None
    project_id: int | None
    deliverable_id: int | None
    message: str
    status: str
    triggered_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None

    model_config = {"from_attributes": True}
