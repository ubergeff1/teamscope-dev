from pydantic import BaseModel, EmailStr, Field


class ConsultantCreate(BaseModel):
    name: str = Field(..., max_length=100)
    email: EmailStr | None = None
    weekly_capacity: float = Field(40.0, ge=0, le=168)
    float_name: str | None = Field(None, max_length=100)
    color: str = Field("#4C9BE8", pattern=r"^#[0-9A-Fa-f]{6}$")
    is_active: bool = True


class ConsultantUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    email: EmailStr | None = None
    weekly_capacity: float | None = Field(None, ge=0, le=168)
    float_name: str | None = Field(None, max_length=100)
    color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    is_active: bool | None = None


class ConsultantOut(BaseModel):
    id: int
    name: str
    email: str | None
    weekly_capacity: float
    float_name: str | None
    color: str
    is_active: bool

    model_config = {"from_attributes": True}
