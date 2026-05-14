from pydantic import BaseModel


class ControlFamilyOut(BaseModel):
    id: int
    code: str
    name: str
    control_count: int

    model_config = {"from_attributes": True}


class ImpactLevelOut(BaseModel):
    id: int
    name: str
    control_families: list[ControlFamilyOut] = []

    model_config = {"from_attributes": True}


class FrameworkOut(BaseModel):
    id: int
    name: str
    description: str | None
    impact_levels: list[ImpactLevelOut] = []

    model_config = {"from_attributes": True}
