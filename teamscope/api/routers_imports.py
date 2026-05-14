"""
Imports router.
POST /api/imports/float           — Upload Float CSV export; silently upsert actuals.
POST /api/imports/monday/parse    — Upload Monday.com export; return parsed sections + columns for UI.
POST /api/imports/monday/apply    — Apply user-selected items with chosen column mappings.

Float CSV format (columns that matter):
  Person, Project, Task, Start Date (ISO), Hours

Monday.com CSV format (real board export):
  Row 1:  Project / board name (single cell, rest empty)
  Row 2:  Creation date metadata (skip)
  Then repeating blocks per section:
    <Section name row>   — single non-empty cell
    <Column header row>  — first cell == "Name"
    <data rows>
    <summary row>        — first cell empty, skip
"""
import csv
import io
from datetime import date, timedelta
from typing import Annotated

# Common date formats found in Monday.com exports
_DATE_FORMATS = ["%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y", "%m-%d-%Y"]


def _parse_date(raw: str) -> date | None:
    raw = raw.strip()
    if not raw:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return date.fromisoformat(raw) if fmt == "%Y-%m-%d" else __import__("datetime").datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.actuals import Actual, ImportLog
from app.models.consultant import Consultant
from app.models.project import Project
from app.models.deliverable import Deliverable
from app.utils.auth import get_current_user

router = APIRouter(prefix="/imports", tags=["imports"])
Auth = Annotated[str, Depends(get_current_user)]
DB = Annotated[Session, Depends(get_db)]


def _monday_of_week(d: date) -> date:
    return d - timedelta(days=d.weekday())


# Monday.com status labels → internal status values
_MONDAY_STATUS_MAP: dict[str, str] = {
    "done": "complete",
    "completed": "complete",
    "complete": "complete",
    "delivered": "delivered",
    "in qa": "in_qa",
    "qa": "in_qa",
    "review": "in_qa",
    "in progress": "in_progress",
    "working on it": "in_progress",
    "in_progress": "in_progress",
    "not started": "not_started",
    "stuck": "not_started",
    "": "not_started",
}


def _map_monday_status(raw: str) -> str:
    return _MONDAY_STATUS_MAP.get(raw.strip().lower(), "not_started")


# ── Float import ──────────────────────────────────────────────────────────────

@router.post("/float")
async def import_float(
    db: DB,
    username: Auth,
    file: UploadFile = File(...),
):
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))

    consultants = {(c.float_name or c.name).lower(): c for c in db.query(Consultant).all()}
    projects = {p.name.lower(): p for p in db.query(Project).all()}

    inserted = updated = skipped = 0
    errors: list[str] = []

    for i, row in enumerate(reader, start=2):
        person = (row.get("Person") or "").strip().lower()
        project_name = (row.get("Project") or "").strip().lower()
        start_raw = (row.get("Start Date") or "").strip()
        hours_raw = (row.get("Hours") or "0").strip()

        c = consultants.get(person)
        p = projects.get(project_name)

        if not c or not p:
            skipped += 1
            continue

        try:
            start = date.fromisoformat(start_raw)
            week_start = _monday_of_week(start)
            hours = float(hours_raw)
        except (ValueError, TypeError) as e:
            errors.append(f"Row {i}: {e}")
            skipped += 1
            continue

        existing = db.query(Actual).filter(
            Actual.consultant_id == c.id,
            Actual.project_id == p.id,
            Actual.week_start == week_start,
        ).first()

        if existing:
            existing.hours = float(existing.hours) + hours
            updated += 1
        else:
            db.add(Actual(
                consultant_id=c.id, project_id=p.id,
                week_start=week_start, hours=hours, source="float",
            ))
            inserted += 1

    import_status = "success" if not errors else "partial"
    db.add(ImportLog(
        source="float_actuals",
        filename=file.filename,
        rows_processed=inserted + updated + skipped,
        rows_inserted=inserted,
        rows_updated=updated,
        rows_skipped=skipped,
        status=import_status,
        error_detail="\n".join(errors) if errors else None,
        created_by=username,
    ))
    db.commit()

    return {
        "status": import_status,
        "rows_processed": inserted + updated + skipped,
        "rows_inserted": inserted,
        "rows_updated": updated,
        "rows_skipped": skipped,
        "errors": errors[:20],
    }


# ── Monday.com import — parse + apply workflow ────────────────────────────────

def _parse_monday_export(content: bytes) -> dict:
    """
    Parse a Monday.com board CSV export into structured sections.

    Returns:
      project_name: str          — first row of the file
      columns: list[str]         — column names from the first header row found
      sections: list of {
        name: str,
        items: list[dict]        — one dict per data row, keyed by column name
      }
    """
    rows = list(csv.reader(io.StringIO(content.decode("utf-8-sig"))))
    if not rows:
        return {"project_name": "", "columns": [], "sections": []}

    project_name = rows[0][0].strip() if rows[0] else ""

    columns: list[str] = []
    sections: list[dict] = []
    current_section: dict | None = None

    for row in rows[1:]:           # skip row 0 (project name)
        cells = [c.strip() for c in row]
        # Pad so index checks are safe
        while len(cells) < 2:
            cells.append("")

        first = cells[0]
        has_other = any(cells[1:])

        # Blank row — skip
        if not any(cells):
            continue

        # Column-header row — first cell is literally "Name"
        if first == "Name":
            if not columns:                  # capture once; they're identical per section
                columns = [c for c in cells if c]
            continue

        # Section-header row — only first cell non-empty
        if first and not has_other:
            current_section = {"name": first, "items": []}
            sections.append(current_section)
            continue

        # Summary / metadata row — first cell empty
        if not first:
            continue

        # Data row
        if current_section is not None and columns:
            item: dict = {}
            for i, col in enumerate(columns):
                item[col] = cells[i] if i < len(cells) else ""
            current_section["items"].append(item)

    return {"project_name": project_name, "columns": columns, "sections": sections}


@router.post("/monday/parse")
async def parse_monday(
    db: DB,
    _: Auth,
    file: UploadFile = File(...),
):
    """
    Upload a Monday.com CSV export.
    Returns the parsed sections/items plus existing projects for matching.
    No database writes.
    """
    content = await file.read()
    parsed = _parse_monday_export(content)

    existing_projects = [
        {"id": p.id, "name": p.name}
        for p in db.query(Project).order_by(Project.name).all()
    ]

    return {**parsed, "existing_projects": existing_projects}


@router.post("/monday/apply")
def apply_monday(
    body: dict,
    db: DB,
    username: Auth,
):
    """
    Apply a Monday.com import with user-chosen column mappings and items.

    body:
      project_id:      int | null   — existing project to import into
      project_name:    str | null   — name for a new project (used when project_id is null)
      name_col:        str          — CSV column to use as deliverable name  (default "Name")
      status_col:      str | null   — CSV column to use as status
      start_date_col:  str | null   — CSV column to use as start date
      end_date_col:    str | null   — CSV column to use as end date
      items:           list[dict]   — pre-filtered rows from the frontend
    """
    project_id: int | None = body.get("project_id")
    project_name: str = (body.get("project_name") or "").strip()
    name_col: str = body.get("name_col") or "Name"
    status_col: str | None = body.get("status_col") or None
    start_date_col: str | None = body.get("start_date_col") or None
    end_date_col: str | None = body.get("end_date_col") or None
    items: list[dict] = body.get("items", [])

    # Resolve or create project
    if not project_id:
        if not project_name:
            return {"error": "project_name required when project_id is not set"}, 400
        project = Project(name=project_name)
        db.add(project)
        db.flush()
        project_id = project.id

    # Fetch existing deliverables for this project to detect updates vs inserts
    existing = {
        d.name.lower(): d
        for d in db.query(Deliverable).filter(Deliverable.project_id == project_id).all()
    }

    inserted = updated = skipped = 0

    for item in items:
        name = (item.get(name_col) or "").strip()
        if not name:
            skipped += 1
            continue

        status = _map_monday_status(item.get(status_col) or "") if status_col else "not_started"
        start = _parse_date(item.get(start_date_col) or "") if start_date_col else None
        end = _parse_date(item.get(end_date_col) or "") if end_date_col else None

        key = name.lower()
        if key in existing:
            d = existing[key]
            d.status = status
            if start is not None:
                d.start_date = start
            if end is not None:
                d.end_date = end
            updated += 1
        else:
            db.add(Deliverable(
                project_id=project_id,
                name=name,
                deliverable_type="custom",
                status=status,
                start_date=start,
                end_date=end,
            ))
            inserted += 1

    db.add(ImportLog(
        source="monday_delta",
        rows_processed=inserted + updated + skipped,
        rows_inserted=inserted,
        rows_updated=updated,
        rows_skipped=skipped,
        status="success",
        created_by=username,
    ))
    db.commit()
    return {"rows_inserted": inserted, "rows_updated": updated, "rows_skipped": skipped}
