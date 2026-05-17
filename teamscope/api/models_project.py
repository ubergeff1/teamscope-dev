"""
Project model — represents a client engagement.

This module defines the core Project entity, which is the top-level organizational
unit in TeamScope. Each project represents a consulting engagement for a specific
client, governed by a compliance framework (e.g., FedRAMP, CMMC) at a particular
impact level.

Projects link to deliverables, workshops, and consultants, forming the backbone
of the capacity planning and tracking system. The monday_project_id field enables
synchronization with Monday.com for delta-matching on re-import.

The color field is auto-assigned from the application palette on creation and can
be overridden by the user for visual distinction in the UI grid.
"""
from sqlalchemy import Integer, String, Text, Date, Boolean, ForeignKey, DateTime, Table, Column, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base


# Many-to-many association table linking projects to their assigned consultants.
# Uses CASCADE deletes on both sides so that removing a project or consultant
# automatically cleans up the association rows. This table has no additional
# columns — it is a pure join table.
project_consultants = Table(
    "project_consultants",
    Base.metadata,
    Column("project_id", Integer, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("consultant_id", Integer, ForeignKey("consultants.id", ondelete="CASCADE"), primary_key=True),
)


class Project(Base):
    """
    A client consulting engagement tracked by TeamScope.

    Projects serve as the primary container for all work items (deliverables
    and workshops). Each project optionally references a compliance framework
    and impact level, which together determine the applicable control families
    and, by extension, the set of deliverables that need to be completed.

    Key behaviors:
    - Status lifecycle: active -> on_hold -> complete -> archived
    - budgeted_hours is the total contracted hours for variance tracking
    - snap_end_to_friday, when True, causes auto-scheduling logic to align
      the project end date to the nearest Friday (avoids partial weeks)
    - Consultants are associated via the project_consultants join table
    """
    __tablename__ = "projects"

    # Primary key — auto-incrementing integer.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Human-readable project name, displayed in navigation and reports.
    # Max 200 characters; required field.
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Name of the client organization. Optional; used for filtering and display.
    client_name: Mapped[str | None] = mapped_column(String(200))

    # FK to the compliance framework (e.g., FedRAMP, GovRAMP, CMMC).
    # Nullable because a project may be created before the framework is decided.
    framework_id: Mapped[int | None] = mapped_column(ForeignKey("frameworks.id"))

    # FK to the impact level within the chosen framework (e.g., Low, Moderate, High).
    # Together with framework_id, determines which control families apply.
    impact_level_id: Mapped[int | None] = mapped_column(ForeignKey("impact_levels.id"))

    # Planned start date of the engagement. Used for scheduling and timeline views.
    start_date: Mapped[Date | None] = mapped_column(Date)

    # Planned end date of the engagement. May be snapped to Friday if snap_end_to_friday is True.
    end_date: Mapped[Date | None] = mapped_column(Date)

    # Current lifecycle status of the project.
    # Valid values: active | on_hold | complete | archived
    # Defaults to "active" when a new project is created.
    status: Mapped[str] = mapped_column(String(30), default="active")

    # External ID from Monday.com. Used for delta-matching during re-import
    # to detect new vs. existing projects. Null if the project was not imported.
    monday_project_id: Mapped[str | None] = mapped_column(String(100))

    # Hex color code (e.g., "#4C9BE8") used for visual identification in the
    # capacity grid and Gantt charts. Auto-assigned from the palette on creation.
    color: Mapped[str] = mapped_column(String(7), default="#4C9BE8")

    # Free-form notes about the project. Supports longer text for context,
    # assumptions, or special instructions.
    notes: Mapped[str | None] = mapped_column(Text)

    # Total budgeted hours for the engagement as specified in the contract.
    # Compared against actual hours to calculate budget variance.
    # Precision: up to 999,999.99 hours.
    budgeted_hours: Mapped[float | None] = mapped_column(Numeric(8, 2))

    # When True, the auto-scheduling engine will adjust the project end_date
    # to the nearest Friday, preventing deliverables from ending mid-week.
    snap_end_to_friday: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamp of when this project record was first created. Set automatically
    # by the database server on INSERT.
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Timestamp of the last modification. Automatically updated by SQLAlchemy
    # on every UPDATE via the onupdate trigger.
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # --- Relationships ---

    # The compliance framework this project follows. Lazy-loaded by default.
    framework: Mapped["Framework | None"] = relationship("Framework")  # type: ignore

    # The impact level within the framework. Determines control family scope.
    impact_level: Mapped["ImpactLevel | None"] = relationship("ImpactLevel")  # type: ignore

    # All deliverables belonging to this project. Cascade delete ensures
    # deliverables are removed when the project is deleted.
    deliverables: Mapped[list["Deliverable"]] = relationship(  # type: ignore
        "Deliverable", back_populates="project", cascade="all, delete-orphan"
    )

    # All workshops belonging to this project. Cascade delete ensures
    # workshops are removed when the project is deleted.
    workshops: Mapped[list["Workshop"]] = relationship(  # type: ignore
        "Workshop", back_populates="project", cascade="all, delete-orphan"
    )

    # Consultants assigned to this project via the project_consultants join table.
    # Uses "selectin" loading to efficiently batch-load consultants when
    # querying multiple projects.
    consultants: Mapped[list["Consultant"]] = relationship(  # type: ignore
        "Consultant", secondary="project_consultants", lazy="selectin"
    )
