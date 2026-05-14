"""
AppSetting model — key/value store for all configurable application settings.
Stored in the database so settings survive container restarts without env-var changes.

Example keys:
  ui.theme              = "dark" | "light"
  ui.grid_density       = "compact" | "normal" | "comfortable"
  ui.default_week_span  = "12"          (number of weeks shown in grid by default)
  alert.email_enabled   = "false"
  alert.smtp_host       = "smtp.example.com"
  capacity.warn_pct     = "85"          (yellow threshold)
  capacity.danger_pct   = "100"         (red threshold)
  color.palette         = '["#4C9BE8","#E87C4C",...]'  (JSON array)
"""
from sqlalchemy import Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.database import Base


class AppSetting(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(String(300))
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
