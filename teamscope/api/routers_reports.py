"""
Reports router.
Manages saved report configurations and runs them on-demand.
Export endpoints stream files back to the client.
"""
import csv
import io
import json
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.report import ReportConfig
from app.models.assignment import WeeklyAllocation
from app.models.actuals import Actual
from app.models.consultant import Consultant
from app.models.project import Project
from app.schemas.report import ReportConfigCreate, ReportConfigUpdate, ReportConfigOut
from app.utils.auth import get_current_user

router = APIRouter(prefix="/reports", tags=["reports"])
Auth = Annotated[str, Depends(get_current_user)]
DB = Annotated[Session, Depends(get_db)]


# ── Config CRUD ───────────────────────────────────────────────────────────────

@router.get("/configs", response_model=list[ReportConfigOut])
def list_report_configs(db: DB, _: Auth):
    return db.query(ReportConfig).order_by(ReportConfig.is_pinned.desc(), ReportConfig.name).all()


@router.post("/configs", response_model=ReportConfigOut, status_code=201)
def create_report_config(body: ReportConfigCreate, db: DB, username: Auth):
    rc = ReportConfig(**body.model_dump(), created_by=username)
    db.add(rc)
    db.commit()
    db.refresh(rc)
    return rc


@router.patch("/configs/{config_id}", response_model=ReportConfigOut)
def update_report_config(config_id: int, body: ReportConfigUpdate, db: DB, _: Auth):
    rc = db.get(ReportConfig, config_id)
    if not rc:
        raise HTTPException(status_code=404, detail="Report config not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(rc, field, value)
    db.commit()
    db.refresh(rc)
    return rc


@router.delete("/configs/{config_id}", status_code=204)
def delete_report_config(config_id: int, db: DB, _: Auth):
    rc = db.get(ReportConfig, config_id)
    if not rc:
        raise HTTPException(status_code=404, detail="Report config not found")
    db.delete(rc)
    db.commit()


# ── Run / Export ──────────────────────────────────────────────────────────────

@router.get("/configs/{config_id}/export/csv")
def export_report_csv(config_id: int, db: DB, _: Auth):
    """Run a saved report and stream it as a CSV file."""
    rc = db.get(ReportConfig, config_id)
    if not rc:
        raise HTTPException(status_code=404, detail="Report config not found")

    filters = json.loads(rc.filters or "{}")
    date_from = date.fromisoformat(filters.get("date_from", "2020-01-01"))
    date_to = date.fromisoformat(filters.get("date_to", "2099-12-31"))
    c_ids = filters.get("consultant_ids") or None
    p_ids = filters.get("project_ids") or None

    rows = _run_capacity_grid_query(db, date_from, date_to, c_ids, p_ids)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["consultant", "project", "week_start", "planned_hours", "actual_hours"])
    writer.writeheader()
    writer.writerows(rows)
    output.seek(0)

    filename = f"{rc.name.replace(' ', '_')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _run_capacity_grid_query(
    db: Session,
    date_from: date,
    date_to: date,
    consultant_ids: list[int] | None,
    project_ids: list[int] | None,
) -> list[dict]:
    """Returns rows: consultant, project, week_start, planned_hours, actual_hours."""
    consultants = {c.id: c.name for c in db.query(Consultant).all()}
    projects = {p.id: p.name for p in db.query(Project).all()}

    planned_q = (
        db.query(
            WeeklyAllocation.consultant_id,
            WeeklyAllocation.project_id,
            WeeklyAllocation.week_start,
            func.sum(WeeklyAllocation.hours).label("planned"),
        )
        .filter(WeeklyAllocation.week_start.between(date_from, date_to))
        .group_by(WeeklyAllocation.consultant_id, WeeklyAllocation.project_id, WeeklyAllocation.week_start)
    )
    if consultant_ids:
        planned_q = planned_q.filter(WeeklyAllocation.consultant_id.in_(consultant_ids))
    if project_ids:
        planned_q = planned_q.filter(WeeklyAllocation.project_id.in_(project_ids))

    # Build actuals lookup
    actual_q = db.query(Actual).filter(Actual.week_start.between(date_from, date_to))
    if consultant_ids:
        actual_q = actual_q.filter(Actual.consultant_id.in_(consultant_ids))
    if project_ids:
        actual_q = actual_q.filter(Actual.project_id.in_(project_ids))
    actuals_map = {}
    for a in actual_q.all():
        actuals_map[(a.consultant_id, a.project_id, a.week_start)] = float(a.hours)

    rows = []
    for r in planned_q.all():
        rows.append({
            "consultant": consultants.get(r.consultant_id, str(r.consultant_id)),
            "project": projects.get(r.project_id, str(r.project_id)),
            "week_start": r.week_start.isoformat(),
            "planned_hours": float(r.planned),
            "actual_hours": actuals_map.get((r.consultant_id, r.project_id, r.week_start), 0.0),
        })
    return rows
