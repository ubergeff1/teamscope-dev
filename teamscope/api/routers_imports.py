"""
Imports router — handles CSV data imports from external tools (Float, Monday.com).

API prefix: /api/imports
Tags: ["imports"]

This router provides three endpoints:

  POST /api/imports/float
    Upload a Float CSV export; silently upsert actual hours into the system.
    Matches rows by consultant name and project name, aggregating hours by week.

  POST /api/imports/monday/parse
    Upload a Monday.com board CSV export; returns parsed sections, columns,
    and items for the frontend to display a mapping UI. No database writes.

  POST /api/imports/monday/apply
    Apply user-selected items from a parsed Monday.com export with chosen
    column mappings. Creates or updates deliverables in the target project.

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

# Common date formats found in Monday.com exports, tried in order
_DATE_FORMATS = ["%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y", "%m-%d-%Y"]


def _parse_date(raw: str) -> date | None:
    """Parse a date string trying multiple common formats.

    Attempts ISO format first, then falls back to strptime with each
    format in _DATE_FORMATS. Used for Monday.com date columns which
    may use different regional formats.

    Args:
        raw: The raw date string from a CSV cell.

    Returns:
        A date object if parsing succeeds, None otherwise.
    """
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

# Create the FastAPI router with /imports prefix
router = APIRouter(prefix="/imports", tags=["imports"])

# Type aliases for dependency injection
# Auth: extracts the authenticated username from the JWT token
Auth = Annotated[str, Depends(get_current_user)]
# DB: provides a SQLAlchemy database session
DB = Annotated[Session, Depends(get_db)]


def _monday_of_week(d: date) -> date:
    """Return the Monday of the week containing the given date.

    Used to normalize dates to week boundaries for weekly aggregation.
    weekday() returns 0 for Monday, so subtracting it gives the Monday.

    Args:
        d: Any date.

    Returns:
        The Monday (start of ISO week) for that date.
    """
    return d - timedelta(days=d.weekday())


# Monday.com status labels -> internal status values
# Maps various status text found in Monday.com exports to the app's
# standardized status enum values.
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
    """Convert a Monday.com status label to an internal status value.

    Performs case-insensitive lookup against _MONDAY_STATUS_MAP.
    Defaults to "not_started" for unrecognized values.

    Args:
        raw: The raw status string from a Monday.com CSV cell.

    Returns:
        The corresponding internal status string.
    """
    return _MONDAY_STATUS_MAP.get(raw.strip().lower(), "not_started")


# ── Float import ──────────────────────────────────────────────────────────────

@router.post("/float")
async def import_float(
    db: DB,
    username: Auth,
    file: UploadFile = File(...),
):
    """POST /imports/float — Import actual hours from a Float CSV export.

    Reads a Float time-tracking CSV and upserts actual hours into the system.
    Hours are aggregated by (consultant, project, week_start).

    Request Body:
        Multipart file upload — the Float CSV export file.

    Returns:
        JSON with import results:
          - status: "success" or "partial" (if some rows had errors)
          - rows_processed: total rows attempted
          - rows_inserted: new Actual records created
          - rows_updated: existing Actual records updated (hours added)
          - rows_skipped: rows skipped (unknown consultant/project or parse errors)
          - errors: first 20 error messages

    Business Logic:
        1. Decode the CSV file (handling UTF-8 BOM).
        2. Build lookup maps: consultant name -> Consultant, project name -> Project.
           Float exports use "Person" for consultant name; we match against both
           float_name and name (case-insensitive).
        3. For each CSV row:
           a. Look up the consultant and project by name. Skip if not found.
           b. Parse the start date and normalize to the Monday of that week.
           c. Check for an existing Actual record for that (consultant, project, week).
           d. If exists: add hours to the existing record (accumulate).
           e. If not: create a new Actual record with source="float".
        4. Log the import in ImportLog for audit trail.
        5. Commit and return the summary.
    """
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))

    # Build lookup maps: lowercase name -> ORM object
    # float_name takes priority over regular name for matching
    consultants = {(c.float_name or c.name).lower(): c for c in db.query(Consultant).all()}
    projects = {p.name.lower(): p for p in db.query(Project).all()}

    inserted = updated = skipped = 0
    errors: list[str] = []

    for i, row in enumerate(reader, start=2):
        person = (row.get("Person") or "").strip().lower()
        project_name = (row.get("Project") or "").strip().lower()
        start_raw = (row.get("Start Date") or "").strip()
        hours_raw = (row.get("Hours") or "0").strip()

        # Look up consultant and project — skip row if either is unknown
        c = consultants.get(person)
        p = projects.get(project_name)

        if not c or not p:
            skipped += 1
            continue

        try:
            start = date.fromisoformat(start_raw)
            week_start = _monday_of_week(start)  # Normalize to Monday of that week
            hours = float(hours_raw)
        except (ValueError, TypeError) as e:
            errors.append(f"Row {i}: {e}")
            skipped += 1
            continue

        # Upsert: check for existing Actual record for this (consultant, project, week)
        existing = db.query(Actual).filter(
            Actual.consultant_id == c.id,
            Actual.project_id == p.id,
            Actual.week_start == week_start,
        ).first()

        if existing:
            # Accumulate hours onto existing record
            existing.hours = float(existing.hours) + hours
            updated += 1
        else:
            # Create new Actual record
            db.add(Actual(
                consultant_id=c.id, project_id=p.id,
                week_start=week_start, hours=hours, source="float",
            ))
            inserted += 1

    # Log the import for audit purposes
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
        "errors": errors[:20],  # Limit error output to first 20
    }


# ── Monday.com import — parse + apply workflow ────────────────────────────────

def _parse_monday_export(content: bytes) -> dict:
    """Parse a Monday.com board CSV export into structured sections.

    Monday.com exports have a specific layout:
      - Row 1: board/project name
      - Row 2: creation metadata (skipped)
      - Then repeating blocks:
          - Section name row (only first cell non-empty)
          - Column header row (first cell is "Name")
          - Data rows
          - Summary row (first cell empty, skipped)

    Args:
        content: Raw bytes of the uploaded CSV file.

    Returns:
        A dict with:
          - project_name (str): The board name from row 1.
          - columns (list[str]): Column headers from the first header row.
          - sections (list[dict]): Each section has:
              - name (str): Section name.
              - items (list[dict]): Data rows as dicts keyed by column name.
    """
    rows = list(csv.reader(io.StringIO(content.decode("utf-8-sig"))))
    if not rows:
        return {"project_name": "", "columns": [], "sections": []}

    # First row contains the board/project name
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

        # Section-header row — only first cell non-empty (no other columns filled)
        if first and not has_other:
            current_section = {"name": first, "items": []}
            sections.append(current_section)
            continue

        # Summary / metadata row — first cell empty (skip these)
        if not first:
            continue

        # Data row — add to current section using column headers as keys
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
    """POST /imports/monday/parse — Parse a Monday.com CSV export for preview.

    Upload a Monday.com CSV export. Returns the parsed sections/items plus
    existing projects for the frontend to build a column-mapping UI.
    No database writes occur — this is a read-only preview step.

    Request Body:
        Multipart file upload — the Monday.com CSV export file.

    Returns:
        JSON with:
          - project_name: board name from the CSV
          - columns: list of column names found
          - sections: list of sections with items
          - existing_projects: list of {id, name} for project matching
    """
    content = await file.read()
    parsed = _parse_monday_export(content)

    # Include existing projects so the frontend can offer a project picker
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
    """POST /imports/monday/apply — Apply parsed Monday.com items as deliverables.

    Apply a Monday.com import with user-chosen column mappings and pre-filtered items.
    Creates or updates deliverables in the target project.

    Request Body (JSON dict):
        project_id (int | null): Existing project to import into.
        project_name (str | null): Name for a new project (used when project_id is null).
        name_col (str): CSV column to use as deliverable name (default "Name").
        status_col (str | null): CSV column to use as status.
        start_date_col (str | null): CSV column to use as start date.
        end_date_col (str | null): CSV column to use as end date.
        items (list[dict]): Pre-filtered rows from the frontend, keyed by column name.

    Returns:
        {"rows_inserted": int, "rows_updated": int, "rows_skipped": int}

    Business Logic:
        1. Resolve or create the target project:
           - If project_id is given, use that project.
           - Otherwise, create a new project from project_name.
        2. Build a lookup of existing deliverables in the project (by lowercase name).
        3. For each item:
           a. Extract the name from the chosen name column. Skip if empty.
           b. Map the status using _map_monday_status if a status column is configured.
           c. Parse start/end dates if those columns are configured.
           d. If a deliverable with the same name exists: update its status/dates.
           e. Otherwise: create a new Deliverable with type "custom".
        4. Log the import and commit.
    """
    # Extract parameters from the request body
    project_id: int | None = body.get("project_id")
    project_name: str = (body.get("project_name") or "").strip()
    name_col: str = body.get("name_col") or "Name"
    status_col: str | None = body.get("status_col") or None
    start_date_col: str | None = body.get("start_date_col") or None
    end_date_col: str | None = body.get("end_date_col") or None
    items: list[dict] = body.get("items", [])

    # Resolve or create the target project
    if not project_id:
        if not project_name:
            return {"error": "project_name required when project_id is not set"}, 400
        project = Project(name=project_name)
        db.add(project)
        db.flush()
        project_id = project.id

    # Build a lookup of existing deliverables for deduplication (update vs insert)
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

        # Map status from Monday.com label to internal value
        status = _map_monday_status(item.get(status_col) or "") if status_col else "not_started"
        # Parse dates from the configured columns
        start = _parse_date(item.get(start_date_col) or "") if start_date_col else None
        end = _parse_date(item.get(end_date_col) or "") if end_date_col else None

        key = name.lower()
        if key in existing:
            # Update existing deliverable with new status and dates
            d = existing[key]
            d.status = status
            if start is not None:
                d.start_date = start
            if end is not None:
                d.end_date = end
            updated += 1
        else:
            # Create new deliverable with type "custom"
            db.add(Deliverable(
                project_id=project_id,
                name=name,
                deliverable_type="custom",
                status=status,
                start_date=start,
                end_date=end,
            ))
            inserted += 1

    # Log the import for audit
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
