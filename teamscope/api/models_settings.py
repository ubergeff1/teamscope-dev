"""
AppSetting model — key/value store for all configurable application settings.

This module defines a simple but flexible settings system backed by the database.
Settings are stored as key/value pairs so they survive container restarts without
requiring environment variable changes or config file mounts.

The key naming convention uses dot-separated namespaces for organization:

  UI settings:
    ui.theme              = "dark" | "light"           -- Controls the application color scheme
    ui.grid_density       = "compact" | "normal" | "comfortable"  -- Row height in data grids
    ui.default_week_span  = "12"                       -- Number of weeks shown in capacity grid by default

  Alert settings:
    alert.email_enabled   = "false"                    -- Whether email notifications are sent for alerts
    alert.smtp_host       = "smtp.example.com"         -- SMTP server hostname for alert emails

  Capacity thresholds:
    capacity.warn_pct     = "85"                       -- Yellow warning threshold for utilization percentage
    capacity.danger_pct   = "100"                      -- Red danger threshold for utilization percentage

  Visual settings:
    color.palette         = '["#4C9BE8","#E87C4C",...]'  -- JSON array of hex colors for auto-assignment

All values are stored as strings (even numbers and booleans) and must be parsed
by the consuming code. This simplifies the schema and avoids type-mismatch issues.
"""
from sqlalchemy import Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.database import Base


class AppSetting(Base):
    """
    A single application configuration setting stored as a key/value pair.

    AppSettings provide a database-backed alternative to environment variables
    for application configuration. They can be read and updated through the
    admin UI without requiring a deployment or restart.

    Keys are dot-separated strings following a namespace convention (e.g.,
    "ui.theme", "capacity.warn_pct"). Values are always stored as strings
    and must be parsed to the appropriate type by the consuming code.

    The unique constraint on key ensures each setting exists at most once.
    The description field provides human-readable context for the admin UI.
    """
    __tablename__ = "app_settings"

    # Primary key — auto-incrementing integer.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # The dot-separated setting key (e.g., "ui.theme", "capacity.warn_pct").
    # Must be unique across all settings. Used as the lookup identifier.
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    # The setting value stored as a string. All types (numbers, booleans,
    # JSON arrays) are serialized to string and must be parsed by consumers.
    # Null indicates the setting exists but has no value (use application default).
    value: Mapped[str | None] = mapped_column(Text)

    # Human-readable description of what this setting controls.
    # Displayed in the admin settings UI to help users understand the impact
    # of changing the value. Max 300 characters.
    description: Mapped[str | None] = mapped_column(String(300))

    # Timestamp of the last modification to this setting's value.
    # Auto-updated by SQLAlchemy on every UPDATE. Useful for auditing
    # when a setting was last changed.
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
