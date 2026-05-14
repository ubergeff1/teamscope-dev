from pydantic import BaseModel, Field

_DELIVERABLE_TYPES = r"^(control_family|appendix|workshop|flat_hours|custom)$"


class DeliverableTemplateOut(BaseModel):
    id: int
    name: str
    deliverable_type: str
    control_family_code: str | None
    default_hours_per_control: float | None
    default_flat_hours: float | None     # consultant hours
    default_qa_hours: float | None
    default_business_days: int | None
    workshop_template_id: int | None
    sort_order: int

    model_config = {"from_attributes": True}


class DeliverableTemplateCreate(BaseModel):
    name: str = Field(..., max_length=200)
    deliverable_type: str = Field("custom", pattern=_DELIVERABLE_TYPES)
    control_family_code: str | None = Field(None, max_length=10)
    default_hours_per_control: float | None = None
    default_flat_hours: float | None = None      # consultant hours
    default_qa_hours: float | None = None
    default_business_days: int | None = None
    workshop_template_id: int | None = None
    sort_order: int = 0


class DeliverableTemplateUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    deliverable_type: str | None = Field(None, pattern=_DELIVERABLE_TYPES)
    control_family_code: str | None = Field(None, max_length=10)
    default_hours_per_control: float | None = None
    default_flat_hours: float | None = None      # consultant hours
    default_qa_hours: float | None = None
    default_business_days: int | None = None
    workshop_template_id: int | None = None
    sort_order: int | None = None


class WorkshopTemplateOut(BaseModel):
    id: int
    name: str
    duration_hours: float | None
    sort_order: int

    model_config = {"from_attributes": True}


class WorkshopTemplateCreate(BaseModel):
    name: str = Field(..., max_length=200)
    duration_hours: float | None = None
    sort_order: int = 0


class WorkshopTemplateUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    duration_hours: float | None = None
    sort_order: int | None = None


class ProjectTemplateCreate(BaseModel):
    name: str = Field(..., max_length=100)
    framework_id: int | None = None
    impact_level_id: int | None = None
    description: str | None = None


class ProjectTemplateUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    framework_id: int | None = None
    impact_level_id: int | None = None
    description: str | None = None


class ProjectTemplateOut(BaseModel):
    id: int
    name: str
    framework_id: int | None
    impact_level_id: int | None
    description: str | None
    deliverable_templates: list[DeliverableTemplateOut] = []
    workshop_templates: list[WorkshopTemplateOut] = []

    model_config = {"from_attributes": True}
