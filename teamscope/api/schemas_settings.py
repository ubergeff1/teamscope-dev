from pydantic import BaseModel, Field


class AppSettingOut(BaseModel):
    key: str
    value: str | None
    description: str | None

    model_config = {"from_attributes": True}


class AppSettingUpdate(BaseModel):
    value: str | None = None


class AppSettingBulkUpdate(BaseModel):
    settings: dict[str, str | None]  # {key: value}
