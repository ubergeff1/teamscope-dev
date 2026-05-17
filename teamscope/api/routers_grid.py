"""
Capacity grid router — aggregated weekly allocation and actuals data for the grid view.

API prefix: /api/grid
Tags: ["grid"]

This router provides two endpoints that power the frontend capacity planning grid:

  GET /api/grid?from=2025-01-06&to=2025-03-31
    Returns a structure the frontend AG Grid can consume directly. Each consultant
    gets a list of weekly entries with planned hours, actual hours, capacity,
    utilization percentage, and a per-project breakdown.

  GET /api/grid/consultant/{id}?from=...&to=...
    Returns deliverable-level weekly breakdown for a single consultant, used for
    the Gantt drill-down panel when clicking a consultant row in the capacity grid.
"""
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from fastapi import HTTPException
from app.database import get_db
from app.models.assignment import WeeklyAllocation, Assignment
from app.models.actuals import Actual
from app.models.consultant import Consultant
from app.models.deliverable import Deliverable, DeliverablePhase
from app.models.project import Project
from app.utils.auth import get_current_user

# Create the FastAPI router with /grid prefix
router = APIRouter(prefix="/grid", tags=["grid"])

# Type aliases for dependency injection
# Auth: extracts the authenticated username from the JWT token
Auth = Annotated[str, Depends(get_current_user)]
# DB: provides a SQLAlchemy database session
DB = Annotated[Session, Depends(get_db)]


@router.get("")
def get_grid(
    db: DB,
    _: Auth,
    date_from: date = Query(..., alias="from"),
    date_to: date = Query(..., alias="to"),
    consultant_ids: list[int] | None = Query(None),
    project_ids: list[int] | None = Query(None),
):
    """GET /grid — Return capacity grid data for all (or filtered) consultants.

    Returns grid data keyed by consultant. Each consultant has a list of week
    entries with planned_hours, actual_hours, capacity_hours, utilization_pct,
    and a per-project breakdown with colors.

    Query Parameters:
        from (date, required): Start of the date range (ISO format, e.g. 2025-01-06).
            Aliased from ``date_from`` — use ``?from=...`` in the URL.
        to (date, required): End of the date range (ISO format).
            Aliased from ``date_to`` — use ``?to=...`` in the URL.
        consultant_ids (list[int], optional): Filter to specific consultant IDs.
        project_ids (list[int], optional): Filter to specific project IDs.

    Returns:
        List of consultant objects, each containing:
          - consultant_id, consultant_name, color, capacity_hours
          - weeks: list of weekly entries with planned/actual hours and project breakdown

    Business Logic:
        1. Query all active consultants (optionally filtered by consultant_ids).
        2. Aggregate planned hours from WeeklyAllocation grouped by
           (consultant_id, project_id, week_start).
        3. Aggregate actual hours from Actual records grouped by
           (consultant_id, project_id, week_start).
        4. Fetch project metadata (name, color) for all projects referenced.
        5. Build lookup dictionaries for planned hours and actual hours.
        6. For each consultant, iterate over all weeks where they have data,
           computing utilization_pct = planned / capacity * 100.
        7. Return the structured response.
    """
    # Step 1: Pull all active consultants, optionally filtered
    consultant_q = db.query(Consultant).filter(Consultant.is_active == True)
    if consultant_ids:
        consultant_q = consultant_q.filter(Consultant.id.in_(consultant_ids))
    consultants = consultant_q.order_by(Consultant.name).all()
    consultant_map = {c.id: c for c in consultants}

    # Step 2: Aggregate planned hours: (consultant_id, project_id, week_start) -> hours
    planned_q = (
        db.query(
            WeeklyAllocation.consultant_id,
            WeeklyAllocation.project_id,
            WeeklyAllocation.week_start,
            func.sum(WeeklyAllocation.hours).label("hours"),
        )
        .filter(
            WeeklyAllocation.week_start >= date_from,
            WeeklyAllocation.week_start <= date_to,
            WeeklyAllocation.consultant_id.in_(consultant_map.keys()),
        )
        .group_by(
            WeeklyAllocation.consultant_id,
            WeeklyAllocation.project_id,
            WeeklyAllocation.week_start,
        )
    )
    if project_ids:
        planned_q = planned_q.filter(WeeklyAllocation.project_id.in_(project_ids))
    planned_rows = planned_q.all()

    # Step 3: Aggregate actual hours: (consultant_id, project_id, week_start) -> hours
    actual_q = (
        db.query(
            Actual.consultant_id,
            Actual.project_id,
            Actual.week_start,
            func.sum(Actual.hours).label("hours"),
        )
        .filter(
            Actual.week_start >= date_from,
            Actual.week_start <= date_to,
            Actual.consultant_id.in_(consultant_map.keys()),
        )
        .group_by(Actual.consultant_id, Actual.project_id, Actual.week_start)
    )
    if project_ids:
        actual_q = actual_q.filter(Actual.project_id.in_(project_ids))
    actual_rows = actual_q.all()

    # Step 4: Fetch project names and colors for the breakdown display
    project_ids_used = {r.project_id for r in planned_rows} | {r.project_id for r in actual_rows}
    projects = {p.id: p for p in db.query(Project).filter(Project.id.in_(project_ids_used)).all()}

    # Step 5: Build lookup dictionaries
    # planned[(consultant_id, week_start)] = {project_id: hours}
    planned: dict[tuple, dict] = {}
    for r in planned_rows:
        key = (r.consultant_id, r.week_start)
        planned.setdefault(key, {})[r.project_id] = float(r.hours)

    # actuals[(consultant_id, week_start)] = total hours (summed across all projects)
    actuals: dict[tuple, float] = {}
    for r in actual_rows:
        key = (r.consultant_id, r.week_start)
        actuals[key] = actuals.get(key, 0.0) + float(r.hours)

    # Step 6: Build the response — one entry per consultant with weekly breakdowns
    result = []
    for c in consultants:
        capacity = float(c.weekly_capacity)

        # Collect all weeks where this consultant has planned or actual data
        weeks_set: set[date] = set()
        for (cid, w) in planned:
            if cid == c.id:
                weeks_set.add(w)
        for (cid, w) in actuals:
            if cid == c.id:
                weeks_set.add(w)

        weeks_data = []
        for week_start in sorted(weeks_set):
            # Per-project breakdown of planned hours for this week
            proj_breakdown = planned.get((c.id, week_start), {})
            total_planned = sum(proj_breakdown.values())
            total_actual = actuals.get((c.id, week_start), 0.0)
            # Utilization = planned / capacity * 100 (0 if no capacity set)
            utilization = round(total_planned / capacity * 100, 1) if capacity else 0.0

            project_list = []
            for pid, hrs in proj_breakdown.items():
                proj = projects.get(pid)
                project_list.append({
                    "project_id": pid,
                    "project_name": proj.name if proj else str(pid),
                    "color": proj.color if proj else "#cccccc",
                    "hours": hrs,
                })

            weeks_data.append({
                "week_start": week_start.isoformat(),
                "planned_hours": round(total_planned, 2),
                "actual_hours": round(total_actual, 2),
                "capacity_hours": capacity,
                "utilization_pct": utilization,
                "projects": project_list,
            })

        result.append({
            "consultant_id": c.id,
            "consultant_name": c.name,
            "color": c.color,
            "capacity_hours": capacity,
            "weeks": weeks_data,
        })

    return result


@router.get("/consultant/{consultant_id}")
def get_consultant_gantt(
    consultant_id: int,
    db: DB,
    _: Auth,
    date_from: date = Query(..., alias="from"),
    date_to: date = Query(..., alias="to"),
):
    """GET /grid/consultant/{consultant_id} — Deliverable-level Gantt data for one consultant.

    Returns deliverable-level weekly breakdown for one consultant. Used for the
    Gantt drill-down panel when clicking a consultant row in the capacity grid.

    Path Parameters:
        consultant_id (int): The consultant to get Gantt data for.

    Query Parameters:
        from (date, required): Start of the date range.
        to (date, required): End of the date range.

    Returns:
        A consultant object with nested projects, each containing deliverables
        with phase-level weekly hour breakdowns. Structure:
          {consultant_id, consultant_name, color, capacity_hours, projects: [
            {project_id, project_name, project_color, deliverables: [
              {deliverable_id, deliverable_name, phase_type, weeks: [
                {week_start, hours}
              ]}
            ]}
          ]}

    Business Logic:
        1. Validate the consultant exists (404 if not).
        2. Query WeeklyAllocation joined through Assignment -> DeliverablePhase ->
           Deliverable -> Project to get the full hierarchy.
        3. Group by (week_start, phase_type, deliverable, project) with summed hours.
        4. Build a nested response structure: project -> deliverable/phase -> weeks.
        5. Sort deliverables by name, then by phase order (workshop, draft, qa, delivery).
    """
    consultant = db.get(Consultant, consultant_id)
    if not consultant:
        raise HTTPException(status_code=404, detail="Consultant not found")

    # Join through the full hierarchy: WeeklyAllocation -> Assignment -> Phase -> Deliverable -> Project
    rows = (
        db.query(
            WeeklyAllocation.week_start,
            func.sum(WeeklyAllocation.hours).label("hours"),
            DeliverablePhase.phase_type,
            Deliverable.id.label("deliverable_id"),
            Deliverable.name.label("deliverable_name"),
            Project.id.label("project_id"),
            Project.name.label("project_name"),
            Project.color.label("project_color"),
        )
        .join(Assignment, WeeklyAllocation.assignment_id == Assignment.id)
        .join(DeliverablePhase, Assignment.phase_id == DeliverablePhase.id)
        .join(Deliverable, DeliverablePhase.deliverable_id == Deliverable.id)
        .join(Project, Deliverable.project_id == Project.id)
        .filter(
            WeeklyAllocation.consultant_id == consultant_id,
            WeeklyAllocation.week_start >= date_from,
            WeeklyAllocation.week_start <= date_to,
        )
        .group_by(
            WeeklyAllocation.week_start,
            DeliverablePhase.phase_type,
            Deliverable.id,
            Deliverable.name,
            Project.id,
            Project.name,
            Project.color,
        )
        .order_by(Project.name, Deliverable.name, DeliverablePhase.phase_type, WeeklyAllocation.week_start)
        .all()
    )

    # Build nested structure: project_id -> {deliverables: {(deliverable_id, phase_type) -> entry}}
    proj_map: dict[int, dict] = {}
    for r in rows:
        # Initialize project entry if first time seeing this project
        if r.project_id not in proj_map:
            proj_map[r.project_id] = {
                "project_id": r.project_id,
                "project_name": r.project_name,
                "project_color": r.project_color,
                "deliverables": {},
            }
        deliv_map = proj_map[r.project_id]["deliverables"]
        # Each (deliverable, phase) combo is a separate Gantt bar
        key = (r.deliverable_id, r.phase_type)
        if key not in deliv_map:
            deliv_map[key] = {
                "deliverable_id": r.deliverable_id,
                "deliverable_name": r.deliverable_name,
                "phase_type": r.phase_type,
                "weeks": [],
            }
        # Append the weekly hours for this deliverable/phase
        deliv_map[key]["weeks"].append({
            "week_start": r.week_start.isoformat(),
            "hours": round(float(r.hours), 2),
        })

    # Flatten and sort the nested structure for output
    projects_out = []
    for pd in proj_map.values():
        # Sort deliverables by name, then by phase order (workshop=0, draft=1, qa=2, delivery=3)
        phase_order = {"workshop": 0, "draft": 1, "qa": 2, "delivery": 3}
        deliverables = sorted(
            pd["deliverables"].values(),
            key=lambda d: (d["deliverable_name"], phase_order.get(d["phase_type"], 9))
        )
        projects_out.append({
            "project_id": pd["project_id"],
            "project_name": pd["project_name"],
            "project_color": pd["project_color"],
            "deliverables": deliverables,
        })

    return {
        "consultant_id": consultant.id,
        "consultant_name": consultant.name,
        "color": consultant.color,
        "capacity_hours": float(consultant.weekly_capacity),
        "projects": projects_out,
    }
