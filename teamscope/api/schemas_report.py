"""
Pydantic schemas for saved Report Configuration CRUD operations.

These schemas validate request/response data for the /reports API endpoints.
They correspond to the SQLAlchemy ``ReportConfig`` model defined in
``models_report.py`` (table: ``report_configs``).

A ReportConfig is a saved, named report definition that users can run on
demand.  Each config specifies:
  - ``report_type``: which dataset to query (capacity grid, project summary, etc.)
  - ``filters``: a JSON string describing filter criteria (date ranges,
    consultant/project IDs, statuses)
  - ``columns``: a JSON string listing which columns to include in the output
  - ``default_format``: the export format used when "Run Report" is clicked

Reports can be pinned to the sidebar for quick access.

Schema pattern:
    - ReportConfigCreate  -- POST /reports  (required fields + defaults)
    - ReportConfigUpdate  -- PATCH /reports/{id}  (all fields optional)
    - ReportConfigOut     -- Response body  (mirrors DB columns)
"""
from datetime import datetime
from pydantic import BaseModel, Field


class ReportConfigCreate(BaseModel):
    """Schema for creating a new report configuration (POST /reports).

    Both ``name`` and ``report_type`` are required.  Filter/column
    definitions are optional and can be added later via update.

    Corresponds to the ``ReportConfig`` SQLAlchemy model
    (table: ``report_configs``).
    """
    # Display name for the report; required, max 150 characters.
    name: str = Field(..., max_length=150)
    # Optional description of what this report shows; max 500 characters.
    description: str | None = Field(None, max_length=500)
    # Type of report determining which dataset is queried.
    # Validated by regex to one of: capacity_grid, project_summary,
    # actuals_vs_planned, consultant_utilization, deliverable_status.
    report_type: str = Field(
        ...,
        pattern=r"^(capacity_grid|project_summary|actuals_vs_planned|consultant_utilization|deliverable_status)$",
    )
    # JSON string defining filter criteria for the report.
    # Example: {"date_from": "2025-01-01", "date_to": "2025-12-31",
    #           "consultant_ids": [1,2,3], "project_ids": [], "statuses": ["active"]}
    filters: str | None = None   # JSON string
    # JSON string listing column keys to include in the output.
    # Example: ["consultant", "project", "week", "planned_hours", "actual_hours"]
    columns: str | None = None   # JSON string
    # Default export format when the report is run.
    # Validated by regex to one of: csv, excel, pdf. Defaults to "csv".
    default_format: str = Field("csv", pattern=r"^(csv|excel|pdf)$")
    # Whether this report is pinned to the sidebar for quick access.
    is_pinned: bool = False


class ReportConfigUpdate(BaseModel):
    """Schema for partially updating a report configuration
    (PATCH /reports/{id}).

    All fields are optional; only non-None values are applied.
    Note: ``report_type`` is not updatable after creation (not included
    in this schema) to prevent breaking saved filter/column definitions.
    """
    # Updated report name; max 150 characters. None = keep current value.
    name: str | None = Field(None, max_length=150)
    # Updated description; max 500 characters. None = keep current value.
    description: str | None = Field(None, max_length=500)
    # Updated filter criteria JSON string. None = keep current value.
    filters: str | None = None
    # Updated column list JSON string. None = keep current value.
    columns: str | None = None
    # Updated default export format; must be csv, excel, or pdf if provided.
    default_format: str | None = Field(None, pattern=r"^(csv|excel|pdf)$")
    # Updated pinned status. None = keep current value.
    is_pinned: bool | None = None


class ReportConfigOut(BaseModel):
    """Response schema for report configuration endpoints.

    Mirrors the ``report_configs`` table columns.  The ``updated_at``
    timestamp is excluded; ``created_at`` is included since it is useful
    for sorting and displaying report metadata.

    ``from_attributes = True`` enables direct construction from a SQLAlchemy
    ``ReportConfig`` ORM instance.
    """
    # Auto-generated primary key.
    id: int
    # Report display name.
    name: str
    # Report description, if set.
    description: str | None
    # Report type: capacity_grid | project_summary | actuals_vs_planned |
    # consultant_utilization | deliverable_status.
    report_type: str
    # JSON string with filter criteria, if set.
    filters: str | None
    # JSON string with column definitions, if set.
    columns: str | None
    # Default export format: csv | excel | pdf.
    default_format: str
    # Whether the report is pinned to the sidebar.
    is_pinned: bool
    # Username of the user who created this report config, if tracked.
    created_by: str | None
    # Timestamp when the report config was created.
    created_at: datetime

    model_config = {"from_attributes": True}
