"""
ReportConfig model — saved custom report definitions.

This module defines the report configuration system that allows users to create,
save, and re-run custom reports. Reports provide analytical views of capacity,
utilization, budget, and deliverable data.

Users can define named reports by selecting:
  - report_type: Which dataset to query (e.g., capacity_grid, project_summary,
    actuals_vs_planned, consultant_utilization, deliverable_status).
  - filters: JSON object describing filter criteria such as date ranges,
    consultant IDs, project IDs, and statuses.
  - columns: JSON array of column keys to include in the output, allowing
    users to customize which data points appear.
  - format: Default export format (CSV, Excel, or PDF) used when "Run Report"
    is clicked.

Reports can be pinned to the sidebar for quick access and exported on demand.
"""
from sqlalchemy import Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.database import Base


class ReportConfig(Base):
    """
    A saved custom report definition that can be re-run and exported.

    ReportConfig stores all the parameters needed to reproduce a specific
    analytical view: the report type, filter criteria, column selection, and
    export format. Users create these via the UI and can pin frequently-used
    reports for quick sidebar access.

    Report configurations are user-facing saved queries — they do not store
    results, only the parameters needed to regenerate them on demand.
    """
    __tablename__ = "report_configs"

    # Primary key — auto-incrementing integer.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Human-readable name for this saved report (e.g., "Q1 Capacity Overview").
    # Displayed in the reports list and sidebar (if pinned).
    name: Mapped[str] = mapped_column(String(150), nullable=False)

    # Optional description explaining what this report shows or when to use it.
    # Max 500 characters.
    description: Mapped[str | None] = mapped_column(String(500))

    # The type of report / dataset to query. Determines the underlying query
    # logic and available filter/column options.
    # Valid values: capacity_grid | project_summary | actuals_vs_planned |
    #               consultant_utilization | deliverable_status
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # JSON-encoded filter criteria object. Structure depends on report_type.
    # Example: {"date_from": "2025-01-01", "date_to": "2025-12-31",
    #           "consultant_ids": [1,2,3], "project_ids": [], "statuses": ["active"]}
    # Null means no filters (return all data).
    filters: Mapped[str | None] = mapped_column(Text)

    # JSON-encoded array of column keys to include in the report output.
    # Example: ["consultant", "project", "week", "planned_hours", "actual_hours"]
    # Null means include all default columns for the report_type.
    columns: Mapped[str | None] = mapped_column(Text)

    # Default export format when the user clicks "Run Report".
    # Valid values: csv | excel | pdf
    default_format: Mapped[str] = mapped_column(String(10), default="csv")

    # Whether this report is pinned to the sidebar for quick access.
    # Pinned reports appear in a dedicated section of the navigation.
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)  # Shows in sidebar quick-access

    # Username or identifier of the person who created this report configuration.
    # Used for ownership tracking and access control.
    created_by: Mapped[str | None] = mapped_column(String(100))

    # Timestamp of when this report configuration was first created.
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Timestamp of the last modification to this report configuration.
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
