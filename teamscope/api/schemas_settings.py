"""
Pydantic schemas for application settings CRUD operations.

These schemas validate request/response data for the /settings API endpoints.
They correspond to the SQLAlchemy ``AppSetting`` model defined in
``models_settings.py`` (table: ``app_settings``).

AppSettings is a key-value store for all configurable application settings.
Settings are stored in the database (rather than environment variables) so
they survive container restarts without requiring redeployment.

Example setting keys and values:
    ui.theme              = "dark" | "light"
    ui.grid_density       = "compact" | "normal" | "comfortable"
    ui.default_week_span  = "12"          (number of weeks shown in grid)
    alert.email_enabled   = "false"
    alert.smtp_host       = "smtp.example.com"
    capacity.warn_pct     = "85"          (yellow utilization threshold)
    capacity.danger_pct   = "100"         (red utilization threshold)
    color.palette         = '["#4C9BE8","#E87C4C",...]'  (JSON array)

Schema pattern:
    - AppSettingOut         -- Response body for individual settings
    - AppSettingUpdate      -- PATCH /settings/{key}  (single setting update)
    - AppSettingBulkUpdate  -- PUT /settings  (batch update multiple settings)
"""
from pydantic import BaseModel, Field


class AppSettingOut(BaseModel):
    """Response schema for a single application setting.

    Mirrors the ``app_settings`` table columns (minus ``id`` and
    ``updated_at``).  The ``key`` serves as the logical identifier in
    API responses.

    ``from_attributes = True`` enables direct construction from a SQLAlchemy
    ``AppSetting`` ORM instance.
    """
    # Setting key (e.g. "ui.theme", "capacity.warn_pct"). Acts as the
    # logical identifier; unique in the database.
    key: str
    # Setting value as a string; interpretation depends on the key.
    # Some values are JSON strings (e.g. color.palette), others are plain
    # strings or stringified numbers/booleans.
    value: str | None
    # Human-readable description of what this setting controls.
    description: str | None

    model_config = {"from_attributes": True}


class AppSettingUpdate(BaseModel):
    """Schema for updating a single setting (PATCH /settings/{key}).

    Only the ``value`` field can be changed; the ``key`` and ``description``
    are immutable via the API (managed through migrations/seeds).
    """
    # New value for the setting. Pass None to clear the value.
    value: str | None = None


class AppSettingBulkUpdate(BaseModel):
    """Schema for updating multiple settings at once (PUT /settings).

    Accepts a dictionary mapping setting keys to their new values.
    Keys that do not exist in the database are ignored.  This is useful
    for the settings UI where multiple values are saved simultaneously.
    """
    # Dictionary of {setting_key: new_value} pairs.
    # Example: {"ui.theme": "dark", "capacity.warn_pct": "90"}
    settings: dict[str, str | None]  # {key: value}
