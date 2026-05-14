"""
Project templates router.
Templates are blueprints that pre-populate deliverables when creating a new project.
POST /api/projects/{id}/apply-template applies a template to an existing project.
"""
import io
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from app.database import get_db
from app.models.template import ProjectTemplate, DeliverableTemplate, WorkshopTemplate
from app.models.reference import ControlFamily
from app.models.deliverable import Deliverable, DeliverablePhase, Workshop
from app.models.project import Project
from app.schemas.template import (
    ProjectTemplateCreate,
    ProjectTemplateUpdate,
    ProjectTemplateOut,
    DeliverableTemplateCreate,
    DeliverableTemplateUpdate,
    DeliverableTemplateOut,
    WorkshopTemplateCreate,
    WorkshopTemplateUpdate,
    WorkshopTemplateOut,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix="/templates", tags=["templates"])
Auth = Annotated[str, Depends(get_current_user)]
DB = Annotated[Session, Depends(get_db)]

_PHASE_TYPES = ["workshop", "draft", "qa", "delivery"]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _load_template(db: Session, template_id: int) -> ProjectTemplate | None:
    return (
        db.query(ProjectTemplate)
        .options(
            selectinload(ProjectTemplate.deliverable_templates),
            selectinload(ProjectTemplate.workshop_templates),
        )
        .filter(ProjectTemplate.id == template_id)
        .first()
    )


def _safe_float(val):
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_int(val):
    if val is None:
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def _styled_header(ws, col, value, font, fill, border):
    cell = ws.cell(row=1, column=col, value=value)
    cell.font = font
    cell.fill = fill
    cell.alignment = Alignment(horizontal="center", wrap_text=True)
    cell.border = border
    return cell


def _note_cell(ws, row, col, value):
    cell = ws.cell(row=row, column=col, value=value)
    cell.font = Font(italic=True, color="666666", size=10)
    return cell


# ── Excel Template Download ────────────────────────────────────────────────────

@router.get("/excel-template")
def download_excel_template(_: Auth):
    """Return a formatted Excel file with instructions, examples, and all fields."""
    wb = Workbook()

    hdr_font = Font(bold=True, size=11, color="FFFFFF")
    hdr_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
    section_font = Font(bold=True, size=11, color="2563EB")
    note_font = Font(italic=True, color="666666", size=10)
    example_font = Font(italic=True, color="AAAAAA")
    thin = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin"),
    )

    # ─── Instructions sheet ───────────────────────────────────────────────
    inst = wb.active
    inst.title = "Instructions"
    inst.sheet_properties.tabColor = "2563EB"
    inst.column_dimensions["A"].width = 90

    rows = [
        ("TEAMSCOPE TEMPLATE IMPORT — INSTRUCTIONS", Font(bold=True, size=14, color="2563EB")),
        ("", None),
        ("This workbook has 4 sheets. Fill in the sheets described below, then upload this file", note_font),
        ("using the 'Import Template' button on the Templates page.", note_font),
        ("Rows that start with 'Example:' are ignored on import — delete or leave them.", note_font),
        ("", None),
        ("═══ SHEET: Template Info ═══", section_font),
        ("  Template Name  (required)  — The name for your template, e.g. 'CMMC Level 2'", None),
        ("  Description    (optional)  — A short description of what this template covers", None),
        ("", None),
        ("═══ SHEET: Workshops ═══", section_font),
        ("  Define workshops that will be created when this template is applied to a project.", None),
        ("  Columns:", None),
        ("    Name              (required)  — Workshop name, e.g. 'Kickoff Workshop'", None),
        ("    Duration (hours)  (optional)  — Length of the workshop in hours, e.g. 1.5", None),
        ("", None),
        ("═══ SHEET: Deliverables ═══", section_font),
        ("  Define deliverables that will be created when this template is applied.", None),
        ("  Columns:", None),
        ("    Name                (required)  — Deliverable name", None),
        ("    Type                (required)  — One of the following values:", None),
        ("        control_family  — A NIST/CMMC control family. Set 'Control Family Code' and 'Hours Per Control'.", None),
        ("        flat_hours      — A fixed-hours deliverable. Set 'Flat Hours'.", None),
        ("        appendix        — An appendix document. Set 'Flat Hours'.", None),
        ("        workshop        — A deliverable tied to a workshop phase. Set 'Flat Hours'.", None),
        ("        custom          — Any other deliverable type. Set 'Flat Hours'.", None),
        ("    Control Family Code (conditional) — e.g. 'AC', 'AU', 'CM'. Only for control_family type.", None),
        ("    Hours Per Control   (conditional) — Hours per individual control. Only for control_family type.", None),
        ("    Flat Hours          (optional)  — Total consultant hours for non-control-family deliverables.", None),
        ("    QA Hours            (optional)  — Hours allocated for QA review.", None),
        ("    Business Days       (optional)  — Number of working days to complete.", None),
        ("    Workshop            (optional)  — Name of a workshop from the Workshops sheet to link this", None),
        ("                                      deliverable to. Must match exactly (case-insensitive).", None),
        ("", None),
        ("═══ HOW WORKSHOP LINKING WORKS ═══", section_font),
        ("  Deliverables can be associated with a workshop. When the template is applied:", None),
        ("  1. Workshops are created first", None),
        ("  2. Each deliverable with a 'Workshop' value is linked to the matching workshop", None),
        ("  3. The workshop name in the Deliverables sheet must match a name in the Workshops sheet", None),
        ("", None),
        ("  Example:  Workshops sheet has 'Scoping Workshop'", None),
        ("            Deliverables sheet has a row with Workshop = 'Scoping Workshop'", None),
        ("            → When applied, that deliverable will be linked to the Scoping Workshop", None),
        ("", None),
        ("═══ TIPS ═══", section_font),
        ("  • You can leave optional fields blank — they will default to empty/null", None),
        ("  • Control family deliverables: hours are calculated as control_count × hours_per_control", None),
        ("    (control_count is determined by the project's impact level when the template is applied)", None),
        ("  • Flat hours deliverables: set the total hours directly in the 'Flat Hours' column", None),
        ("  • Sort order is determined by row order in the spreadsheet", None),
    ]

    for i, (text, font) in enumerate(rows, 1):
        cell = inst.cell(row=i, column=1, value=text)
        if font:
            cell.font = font

    # ─── Template Info sheet ──────────────────────────────────────────────
    info = wb.create_sheet("Template Info")
    info.sheet_properties.tabColor = "16A34A"
    info["A1"] = "Field"
    info["B1"] = "Value"
    for cell in [info["A1"], info["B1"]]:
        cell.font = hdr_font
        cell.fill = hdr_fill
        cell.alignment = Alignment(horizontal="center")
        cell.border = thin

    fields = [
        ("Template Name", ""),
        ("Description", ""),
    ]
    for row_idx, (field, val) in enumerate(fields, start=2):
        c1 = info.cell(row=row_idx, column=1, value=field)
        c1.border = thin
        c1.font = Font(bold=True)
        c2 = info.cell(row=row_idx, column=2, value=val)
        c2.border = thin

    info.column_dimensions["A"].width = 22
    info.column_dimensions["B"].width = 50

    # ─── Workshops sheet ──────────────────────────────────────────────────
    ws_sheet = wb.create_sheet("Workshops")
    ws_sheet.sheet_properties.tabColor = "7C3AED"
    w_headers = ["Name", "Duration (hours)"]
    for col, h in enumerate(w_headers, 1):
        _styled_header(ws_sheet, col, h, hdr_font, hdr_fill, thin)

    w_examples = [
        ("Example: Kickoff Workshop", 2),
        ("Example: Scoping Workshop", 1.5),
        ("Example: Gap Analysis Review", 1),
    ]
    for row_idx, ex in enumerate(w_examples, start=2):
        for col, val in enumerate(ex, 1):
            cell = ws_sheet.cell(row=row_idx, column=col, value=val)
            cell.border = thin
            cell.font = example_font

    ws_sheet.column_dimensions["A"].width = 35
    ws_sheet.column_dimensions["B"].width = 20

    # ─── Deliverables sheet ───────────────────────────────────────────────
    ds = wb.create_sheet("Deliverables")
    ds.sheet_properties.tabColor = "EA580C"
    d_headers = [
        "Name", "Type", "Control Family Code", "Hours Per Control",
        "Flat Hours", "QA Hours", "Business Days", "Workshop",
    ]
    for col, h in enumerate(d_headers, 1):
        _styled_header(ds, col, h, hdr_font, hdr_fill, thin)

    d_examples = [
        ("Example: AC Control Family", "control_family", "AC", 2.5, None, 4, 10, None),
        ("Example: System Security Plan", "flat_hours", None, None, 40, 8, 15, None),
        ("Example: Scoping Deliverable", "workshop", None, None, 8, 2, 5, "Scoping Workshop"),
    ]
    for row_idx, ex in enumerate(d_examples, start=2):
        for col, val in enumerate(ex, 1):
            cell = ds.cell(row=row_idx, column=col, value=val)
            cell.border = thin
            cell.font = example_font

    # Column widths
    col_widths = [35, 18, 22, 18, 12, 12, 14, 28]
    for col, w in enumerate(col_widths, 1):
        ds.column_dimensions[get_column_letter(col)].width = w

    # Notes below examples
    note_row = len(d_examples) + 3
    notes = [
        "Valid Type values: control_family, flat_hours, appendix, workshop, custom",
        "Workshop column: enter the exact workshop name from the Workshops sheet to link a deliverable to it",
        "Control Family Code: only used when Type = control_family (e.g. AC, AU, CM, IA, SC)",
        "Hours Per Control: only used when Type = control_family",
        "Delete the example rows above and enter your own deliverables",
    ]
    for i, note in enumerate(notes):
        _note_cell(ds, note_row + i, 1, note)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=template_import.xlsx"},
    )


# ── Import Excel ──────────────────────────────────────────────────────────────

@router.post("/import-excel", response_model=ProjectTemplateOut, status_code=201)
def import_excel_template(file: UploadFile = File(...), db: DB = None, _: Auth = None):
    """Parse an uploaded Excel file and create a ProjectTemplate with deliverables and workshops."""
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="File must be an Excel file (.xlsx)")

    try:
        wb = load_workbook(file.file, data_only=True)
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read Excel file. Ensure it is a valid .xlsx file.")

    # --- Parse Template Info ---
    if "Template Info" not in wb.sheetnames:
        raise HTTPException(status_code=400, detail="Missing 'Template Info' sheet. Download the template first.")

    info = wb["Template Info"]
    info_map = {}
    for row in info.iter_rows(min_row=2, max_col=2, values_only=True):
        if row[0]:
            info_map[str(row[0]).strip()] = row[1]

    template_name = str(info_map.get("Template Name", "")).strip()
    if not template_name:
        raise HTTPException(status_code=400, detail="Please provide a Template Name in the 'Template Info' sheet")

    description = str(info_map.get("Description", "") or "").strip()

    pt = ProjectTemplate(name=template_name, description=description or None)
    db.add(pt)
    db.flush()

    # --- Parse Workshops first (so deliverables can reference them) ---
    wt_name_map = {}  # lowercase name -> WorkshopTemplate
    if "Workshops" in wb.sheetnames:
        ws_sheet = wb["Workshops"]
        for idx, row in enumerate(ws_sheet.iter_rows(min_row=2, max_col=2, values_only=True)):
            name = str(row[0]).strip() if row[0] else ""
            if not name or name.startswith("Example:"):
                continue
            duration = _safe_float(row[1])
            wt = WorkshopTemplate(
                project_template_id=pt.id,
                name=name,
                duration_hours=duration,
                sort_order=idx,
            )
            db.add(wt)
            db.flush()
            wt_name_map[name.lower()] = wt

    # --- Parse Deliverables ---
    valid_types = {"control_family", "flat_hours", "appendix", "workshop", "custom"}
    if "Deliverables" in wb.sheetnames:
        d_sheet = wb["Deliverables"]
        for idx, row in enumerate(d_sheet.iter_rows(min_row=2, max_col=8, values_only=True)):
            name = str(row[0]).strip() if row[0] else ""
            if not name or name.startswith("Example:"):
                continue
            dtype = str(row[1]).strip().lower() if row[1] else "flat_hours"
            if dtype not in valid_types:
                dtype = "flat_hours"
            cf_code = str(row[2]).strip() if row[2] else None
            hpc = _safe_float(row[3])
            flat = _safe_float(row[4])
            qa = _safe_float(row[5])
            bdays = _safe_int(row[6])

            # Workshop linking (column H)
            ws_ref = str(row[7]).strip().lower() if len(row) > 7 and row[7] else None
            ws_template_id = None
            if ws_ref and ws_ref in wt_name_map:
                ws_template_id = wt_name_map[ws_ref].id

            dt = DeliverableTemplate(
                project_template_id=pt.id,
                name=name,
                deliverable_type=dtype,
                control_family_code=cf_code if dtype == "control_family" else None,
                default_hours_per_control=hpc if dtype == "control_family" else None,
                default_flat_hours=flat,
                default_qa_hours=qa,
                default_business_days=bdays,
                workshop_template_id=ws_template_id,
                sort_order=idx,
            )
            db.add(dt)

    db.commit()
    return _load_template(db, pt.id)


# ── Project Templates ──────────────────────────────────────────────────────────

@router.get("", response_model=list[ProjectTemplateOut])
def list_templates(db: DB, _: Auth):
    return (
        db.query(ProjectTemplate)
        .options(
            selectinload(ProjectTemplate.deliverable_templates),
            selectinload(ProjectTemplate.workshop_templates),
        )
        .order_by(ProjectTemplate.name)
        .all()
    )


@router.post("", response_model=ProjectTemplateOut, status_code=201)
def create_template(body: ProjectTemplateCreate, db: DB, _: Auth):
    t = ProjectTemplate(**body.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.patch("/{template_id}", response_model=ProjectTemplateOut)
def update_template(template_id: int, body: ProjectTemplateUpdate, db: DB, _: Auth):
    t = _load_template(db, template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(t, field, value)
    db.commit()
    db.refresh(t)
    return t


@router.delete("/{template_id}", status_code=204)
def delete_template(template_id: int, db: DB, _: Auth):
    t = db.get(ProjectTemplate, template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(t)
    db.commit()


# ── Deliverable Templates ──────────────────────────────────────────────────────

@router.post("/{template_id}/deliverables", response_model=DeliverableTemplateOut, status_code=201)
def add_deliverable_template(template_id: int, body: DeliverableTemplateCreate, db: DB, _: Auth):
    if not db.get(ProjectTemplate, template_id):
        raise HTTPException(status_code=404, detail="Template not found")
    dt = DeliverableTemplate(project_template_id=template_id, **body.model_dump())
    db.add(dt)
    db.commit()
    db.refresh(dt)
    return dt


@router.patch("/deliverables/{dt_id}", response_model=DeliverableTemplateOut)
def update_deliverable_template(dt_id: int, body: DeliverableTemplateUpdate, db: DB, _: Auth):
    dt = db.get(DeliverableTemplate, dt_id)
    if not dt:
        raise HTTPException(status_code=404, detail="Deliverable template not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(dt, field, value)
    db.commit()
    db.refresh(dt)
    return dt


@router.delete("/deliverables/{dt_id}", status_code=204)
def delete_deliverable_template(dt_id: int, db: DB, _: Auth):
    dt = db.get(DeliverableTemplate, dt_id)
    if not dt:
        raise HTTPException(status_code=404, detail="Deliverable template not found")
    db.delete(dt)
    db.commit()


# ── Workshop Templates ─────────────────────────────────────────────────────────

@router.post("/{template_id}/workshops", response_model=WorkshopTemplateOut, status_code=201)
def add_workshop_template(template_id: int, body: WorkshopTemplateCreate, db: DB, _: Auth):
    if not db.get(ProjectTemplate, template_id):
        raise HTTPException(status_code=404, detail="Template not found")
    wt = WorkshopTemplate(project_template_id=template_id, **body.model_dump())
    db.add(wt)
    db.commit()
    db.refresh(wt)
    return wt


@router.patch("/workshops/{wt_id}", response_model=WorkshopTemplateOut)
def update_workshop_template(wt_id: int, body: WorkshopTemplateUpdate, db: DB, _: Auth):
    wt = db.get(WorkshopTemplate, wt_id)
    if not wt:
        raise HTTPException(status_code=404, detail="Workshop template not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(wt, field, value)
    db.commit()
    db.refresh(wt)
    return wt


@router.delete("/workshops/{wt_id}", status_code=204)
def delete_workshop_template(wt_id: int, db: DB, _: Auth):
    wt = db.get(WorkshopTemplate, wt_id)
    if not wt:
        raise HTTPException(status_code=404, detail="Workshop template not found")
    db.delete(wt)
    db.commit()


# ── Apply Template to Project ─────────────────────────────────────────────────

@router.post("/apply/{project_id}/{template_id}")
def apply_template(project_id: int, template_id: int, db: DB, _: Auth):
    """
    Clone all DeliverableTemplates from the given template onto the project.
    For control_family type deliverables, resolve the control_family_id from the
    project's impact_level and the template's control_family_code.
    """
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    template = _load_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    cf_map: dict[str, ControlFamily] = {}
    if project.impact_level_id:
        cfs = db.query(ControlFamily).filter(
            ControlFamily.impact_level_id == project.impact_level_id
        ).all()
        cf_map = {cf.code: cf for cf in cfs}

    wt_id_map: dict[int, int] = {}
    workshops_created = 0
    for wt in sorted(template.workshop_templates, key=lambda x: x.sort_order):
        w = Workshop(project_id=project_id, name=wt.name, status="scheduled",
                     duration_hours=wt.duration_hours)
        db.add(w)
        db.flush()
        wt_id_map[wt.id] = w.id
        workshops_created += 1

    created = 0
    for dt in sorted(template.deliverable_templates, key=lambda x: x.sort_order):
        cf = cf_map.get(dt.control_family_code or "")
        workshop_id = wt_id_map.get(dt.workshop_template_id) if dt.workshop_template_id else None
        d = Deliverable(
            project_id=project_id,
            name=dt.name,
            deliverable_type=dt.deliverable_type,
            control_family_id=cf.id if cf else None,
            control_count=cf.control_count if cf else None,
            hours_per_control=dt.default_hours_per_control,
            flat_hours=dt.default_flat_hours,
            qa_hours=dt.default_qa_hours,
            business_days=dt.default_business_days,
            workshop_id=workshop_id,
            sort_order=dt.sort_order,
        )
        db.add(d)
        db.flush()
        phase_types = _PHASE_TYPES if dt.deliverable_type == "workshop" else _PHASE_TYPES[1:]
        for i, pt_type in enumerate(phase_types):
            db.add(DeliverablePhase(deliverable_id=d.id, phase_type=pt_type, sort_order=i))
        created += 1

    db.commit()
    return {"deliverables_created": created, "workshops_created": workshops_created}
