"""
Settings router — API prefix: /settings

Manages application-wide configuration settings stored as key-value pairs
in the database. Settings control UI behavior, capacity thresholds, alert
email configuration, color palettes, and scheduling options.

Default settings are auto-seeded on first access if they don't exist yet.

Endpoints:
  GET   /settings            — List all settings (seeds defaults if needed)
  PATCH /settings/{key}      — Update a single setting by key
  PATCH /settings            — Bulk update multiple settings at once
"""
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.settings import AppSetting
from app.schemas.settings import AppSettingOut, AppSettingUpdate, AppSettingBulkUpdate
from app.utils.auth import get_current_user

# Router setup: all endpoints prefixed with /settings, grouped under "settings" tag
router = APIRouter(prefix="/settings", tags=["settings"])
# Type aliases for dependency injection
Auth = Annotated[str, Depends(get_current_user)]
DB = Annotated[Session, Depends(get_db)]

# Default settings seeded on first access.
# Each entry maps a dot-namespaced key to a (default_value, description) tuple.
# These define the full set of configurable application settings.
DEFAULTS: dict[str, tuple[str, str]] = {
    # UI settings — control frontend appearance and behavior
    "ui.theme": ("light", "UI color theme: light | dark"),
    "ui.grid_density": ("normal", "Grid row density: compact | normal | comfortable"),
    "ui.default_week_span": ("12", "Number of weeks shown in grid by default"),
    # Capacity thresholds — define warning/danger levels for utilization percentage
    "capacity.warn_pct": ("85", "Utilization % that triggers yellow warning"),
    "capacity.danger_pct": ("100", "Utilization % that triggers red warning"),
    # Alert email settings — SMTP configuration for sending alert notifications
    "alert.email_enabled": ("false", "Enable email notifications for alerts"),
    "alert.smtp_host": ("", "SMTP server hostname"),
    "alert.smtp_port": ("587", "SMTP server port"),
    "alert.smtp_user": ("", "SMTP username"),
    "alert.smtp_password": ("", "SMTP password (stored in plaintext — use env vars for production)"),
    "alert.from_address": ("", "From address for alert emails"),
    # Color palette — available colors for the project/consultant color pickers
    "color.palette": (
        '["#4C9BE8","#E87C4C","#5CB85C","#F0AD4E","#9B59B6","#1ABC9C","#E74C3C","#3498DB"]',
        "JSON array of hex colors available for project/consultant color picker",
    ),
    # Scheduling options — control how dates are calculated for deliverables
    "scheduling.snap_end_to_friday": (
        "false",
        "When enabled, the consultant due date snaps to the Friday of the week the work is due.",
    ),
}


def _ensure_defaults(db: Session) -> None:
    """Insert any missing default settings into the database.

    Called before each read operation to ensure all expected settings exist.
    Only inserts settings whose keys are not already present, making it
    safe to call repeatedly (idempotent).
    """
    existing_keys = {s.key for s in db.query(AppSetting.key).all()}
    for key, (value, description) in DEFAULTS.items():
        if key not in existing_keys:
            db.add(AppSetting(key=key, value=value, description=description))
    db.commit()


@router.get("", response_model=list[AppSettingOut])
def list_settings(db: DB, _: Auth):
    """GET /settings — List all application settings.

    Seeds any missing default settings before returning the full list.
    Returns settings ordered alphabetically by key.
    """
    _ensure_defaults(db)
    return db.query(AppSetting).order_by(AppSetting.key).all()


@router.patch("/{key}", response_model=AppSettingOut)
def update_setting(key: str, body: AppSettingUpdate, db: DB, _: Auth):
    """PATCH /settings/{key} — Update a single setting by its key.

    If the key already exists, updates its value. If the key does not exist,
    creates a new ad-hoc setting (allows extending settings without code changes).
    Seeds defaults first to ensure consistency.
    """
    _ensure_defaults(db)
    s = db.query(AppSetting).filter(AppSetting.key == key).first()
    if not s:
        # Allow creating ad-hoc keys that aren't in the DEFAULTS list
        s = AppSetting(key=key)
        db.add(s)
    s.value = body.value
    db.commit()
    db.refresh(s)
    return s


@router.patch("", response_model=list[AppSettingOut])
def bulk_update_settings(body: AppSettingBulkUpdate, db: DB, _: Auth):
    """PATCH /settings — Bulk update multiple settings at once.

    Accepts a dictionary of {key: value} pairs and updates or creates each one.
    This is more efficient than individual PATCH calls when updating several
    settings simultaneously (e.g., saving a settings form).

    Returns the list of all updated/created settings.
    """
    _ensure_defaults(db)
    results = []
    for key, value in body.settings.items():
        s = db.query(AppSetting).filter(AppSetting.key == key).first()
        if not s:
            # Create new setting if key doesn't exist
            s = AppSetting(key=key)
            db.add(s)
        s.value = value
        results.append(s)
    db.commit()
    # Refresh all updated settings to return current database state
    for s in results:
        db.refresh(s)
    return results
