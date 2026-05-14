from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.settings import AppSetting
from app.schemas.settings import AppSettingOut, AppSettingUpdate, AppSettingBulkUpdate
from app.utils.auth import get_current_user

router = APIRouter(prefix="/settings", tags=["settings"])
Auth = Annotated[str, Depends(get_current_user)]
DB = Annotated[Session, Depends(get_db)]

# Default settings seeded on first access
DEFAULTS: dict[str, tuple[str, str]] = {
    "ui.theme": ("light", "UI color theme: light | dark"),
    "ui.grid_density": ("normal", "Grid row density: compact | normal | comfortable"),
    "ui.default_week_span": ("12", "Number of weeks shown in grid by default"),
    "capacity.warn_pct": ("85", "Utilization % that triggers yellow warning"),
    "capacity.danger_pct": ("100", "Utilization % that triggers red warning"),
    "alert.email_enabled": ("false", "Enable email notifications for alerts"),
    "alert.smtp_host": ("", "SMTP server hostname"),
    "alert.smtp_port": ("587", "SMTP server port"),
    "alert.smtp_user": ("", "SMTP username"),
    "alert.smtp_password": ("", "SMTP password (stored in plaintext — use env vars for production)"),
    "alert.from_address": ("", "From address for alert emails"),
    "color.palette": (
        '["#4C9BE8","#E87C4C","#5CB85C","#F0AD4E","#9B59B6","#1ABC9C","#E74C3C","#3498DB"]',
        "JSON array of hex colors available for project/consultant color picker",
    ),
    "scheduling.snap_end_to_friday": (
        "false",
        "When enabled, the consultant due date snaps to the Friday of the week the work is due.",
    ),
}


def _ensure_defaults(db: Session) -> None:
    """Insert any missing default settings on first call."""
    existing_keys = {s.key for s in db.query(AppSetting.key).all()}
    for key, (value, description) in DEFAULTS.items():
        if key not in existing_keys:
            db.add(AppSetting(key=key, value=value, description=description))
    db.commit()


@router.get("", response_model=list[AppSettingOut])
def list_settings(db: DB, _: Auth):
    _ensure_defaults(db)
    return db.query(AppSetting).order_by(AppSetting.key).all()


@router.patch("/{key}", response_model=AppSettingOut)
def update_setting(key: str, body: AppSettingUpdate, db: DB, _: Auth):
    _ensure_defaults(db)
    s = db.query(AppSetting).filter(AppSetting.key == key).first()
    if not s:
        # Allow creating ad-hoc keys
        s = AppSetting(key=key)
        db.add(s)
    s.value = body.value
    db.commit()
    db.refresh(s)
    return s


@router.patch("", response_model=list[AppSettingOut])
def bulk_update_settings(body: AppSettingBulkUpdate, db: DB, _: Auth):
    _ensure_defaults(db)
    results = []
    for key, value in body.settings.items():
        s = db.query(AppSetting).filter(AppSetting.key == key).first()
        if not s:
            s = AppSetting(key=key)
            db.add(s)
        s.value = value
        results.append(s)
    db.commit()
    for s in results:
        db.refresh(s)
    return results
