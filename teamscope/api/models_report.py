"""
ReportConfig model — saved custom report definitions.

Users can define named reports by selecting:
  - report_type: which dataset to query (capacity_grid, project_summary, actuals_vs_planned, etc.)
  - filters: JSON object describing filter criteria (date ranges, consultants, projects, statuses)
  - columns: JSON array of column keys to include in the output
  - format: default export format when "Run Report" is clicked

Reports can be run on-demand and exported to CSV, Excel, or PDF.
"""
from sqlalchemy import Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.database import Base


class ReportConfig(Base):
    __tablename__ = "report_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    # capacity_grid | project_summary | actuals_vs_planned | consultant_utilization | deliverable_status
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # JSON object: {"date_from": "2025-01-01", "date_to": "2025-12-31",
    #               "consultant_ids": [1,2,3], "project_ids": [], "statuses": ["active"]}
    filters: Mapped[str | None] = mapped_column(Text)
    # JSON array of column keys: ["consultant", "project", "week", "planned_hours", "actual_hours"]
    columns: Mapped[str | None] = mapped_column(Text)
    # csv | excel | pdf
    default_format: Mapped[str] = mapped_column(String(10), default="csv")
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)  # Shows in sidebar quick-access
    created_by: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
