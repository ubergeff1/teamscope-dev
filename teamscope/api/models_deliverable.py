"""
Deliverable, Workshop, and DeliverablePhase models.

This module defines the work items within a project:

Deliverable: A documentation or implementation task (e.g., an AC control family
  implementation for FedRAMP). Deliverables come in several types, each with
  different hour-calculation logic:
  - control_family: total_hours = control_count * hours_per_control
  - flat_hours: total_hours = flat_hours (a fixed number)
  - appendix: supplementary document with flat hours
  - workshop: hours derived from an associated workshop session
  - custom: user-defined hours with no formula

Workshop: A scheduled interactive session with a client (e.g., kickoff meeting,
  control walkthrough). Workshops have their own lifecycle and can have multiple
  consultants assigned.

DeliverablePhase: Each deliverable progresses through up to 4 sequential phases:
  workshop -> draft -> qa -> delivery
  Each phase has its own date range, hour allocation, status, and consultant
  assignments, enabling granular tracking of work progress.
"""
from sqlalchemy import Integer, String, Text, Numeric, Date, Boolean, ForeignKey, DateTime, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base

# Many-to-many association table linking workshops to their assigned consultants.
# A workshop can have multiple consultants (e.g., lead + support), and a
# consultant can participate in multiple workshops. Uses CASCADE deletes on
# both sides for automatic cleanup.
workshop_consultants = Table(
    "workshop_consultants",
    Base.metadata,
    Column("workshop_id", Integer, ForeignKey("workshops.id", ondelete="CASCADE"), primary_key=True),
    Column("consultant_id", Integer, ForeignKey("consultants.id", ondelete="CASCADE"), primary_key=True),
)


class Deliverable(Base):
    """
    A discrete work item within a project that must be completed and delivered.

    Deliverables represent the individual tasks or documents that make up a
    consulting engagement. They are the primary unit of work tracking — each
    deliverable has planned hours, a status lifecycle, optional consultant
    assignments, and phases that break the work into stages.

    Hour calculation depends on deliverable_type:
    - control_family: hours = control_count * hours_per_control
    - flat_hours / appendix / custom: hours = flat_hours
    - workshop: hours derived from linked workshop duration

    Status lifecycle: not_started -> in_progress -> in_qa -> delivered -> complete
    """
    __tablename__ = "deliverables"

    # Primary key — auto-incrementing integer.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # FK to the parent project. CASCADE delete ensures deliverables are removed
    # when their project is deleted.
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))

    # Display name of the deliverable (e.g., "AC - Access Control", "SSP Appendix A").
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Determines the hour-calculation formula and UI behavior.
    # Valid values: control_family | appendix | workshop | flat_hours | custom
    deliverable_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # FK to the control family from the reference data (e.g., AC, AU, CA).
    # Only applicable when deliverable_type is "control_family". Null otherwise.
    control_family_id: Mapped[int | None] = mapped_column(ForeignKey("control_families.id"))

    # Number of controls in the family. Used with hours_per_control to calculate
    # total hours for control_family type deliverables.
    control_count: Mapped[int | None] = mapped_column(Integer)

    # Hours budgeted per individual control. Multiplied by control_count to get
    # the total consultant hours for control_family type deliverables.
    hours_per_control: Mapped[float | None] = mapped_column(Numeric(5, 2))

    # Fixed consultant hours for flat_hours/appendix/custom type deliverables.
    # For control_family types, this field is typically calculated and stored
    # as the product of control_count * hours_per_control.
    flat_hours: Mapped[float | None] = mapped_column(Numeric(6, 2))   # consultant hours

    # Hours allocated for the QA/review phase of this deliverable.
    # Tracked separately from consultant drafting hours for capacity planning.
    qa_hours: Mapped[float | None] = mapped_column(Numeric(6, 2))

    # Number of business days allocated for the drafting phase.
    # Used by the auto-scheduler to calculate end dates from start dates.
    business_days: Mapped[int | None] = mapped_column(Integer)

    # Number of business days allocated for the QA phase.
    # Used by the auto-scheduler to calculate QA end dates.
    qa_business_days: Mapped[int | None] = mapped_column(Integer)

    # When True, the workshop phase must complete before the draft phase can begin.
    # When False, workshop and draft phases may overlap in the schedule.
    workshop_sequential: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")

    # When True, the QA phase must start only after the draft phase completes.
    # When False, QA can overlap with drafting (e.g., rolling review).
    qa_sequential: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")

    # Current lifecycle status of the deliverable.
    # Valid values: not_started | in_progress | in_qa | delivered | complete
    status: Mapped[str] = mapped_column(String(30), default="not_started")

    # Planned start date for this deliverable. May be auto-calculated by the
    # scheduling engine or manually set by the user.
    start_date: Mapped[Date | None] = mapped_column(Date)

    # Planned end date for this deliverable. May be auto-calculated based on
    # start_date + business_days, skipping weekends and holidays.
    end_date: Mapped[Date | None] = mapped_column(Date)

    # FK to an optional associated workshop. SET NULL on workshop deletion
    # so the deliverable survives even if the workshop is removed.
    workshop_id: Mapped[int | None] = mapped_column(ForeignKey("workshops.id", ondelete="SET NULL"))

    # FK to the primary consultant assigned to draft this deliverable.
    # SET NULL on consultant deletion to preserve the deliverable record.
    consultant_id: Mapped[int | None] = mapped_column(ForeignKey("consultants.id", ondelete="SET NULL"))

    # FK to the consultant assigned to perform QA/review of this deliverable.
    # Typically a different person from the primary consultant for separation of duties.
    qa_consultant_id: Mapped[int | None] = mapped_column(ForeignKey("consultants.id", ondelete="SET NULL"))

    # External ID from Monday.com for this deliverable item.
    # Used for delta-matching during synchronization/import.
    monday_item_id: Mapped[str | None] = mapped_column(String(100))

    # Integer controlling the display order of deliverables within a project.
    # Lower values appear first. Defaults to 0.
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamp of when this deliverable was first created.
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Timestamp of the last modification, auto-updated by SQLAlchemy on every UPDATE.
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # --- Relationships ---

    # Back-reference to the parent project.
    project: Mapped["Project"] = relationship("Project", back_populates="deliverables")  # type: ignore

    # The control family from reference data (e.g., AC, AU). Only populated
    # when deliverable_type is "control_family".
    control_family: Mapped["ControlFamily | None"] = relationship("ControlFamily")  # type: ignore

    # Ordered list of phases (workshop, draft, qa, delivery) for this deliverable.
    # Cascade delete ensures phases are removed with the deliverable.
    # Ordered by sort_order for consistent phase sequencing.
    phases: Mapped[list["DeliverablePhase"]] = relationship(
        back_populates="deliverable", cascade="all, delete-orphan", order_by="DeliverablePhase.sort_order"
    )

    @property
    def total_planned_hours(self) -> float:
        """
        Sum of consultant drafting hours and QA review hours.

        Returns the total planned effort for this deliverable by combining
        flat_hours (drafting) and qa_hours (review). Treats None values as zero.
        Used for budget tracking and variance analysis against actual hours.
        """
        return float(self.flat_hours or 0) + float(self.qa_hours or 0)


class Workshop(Base):
    """
    A scheduled interactive session with a client as part of a project.

    Workshops represent meetings such as kickoff sessions, control walkthroughs,
    or review meetings. They have their own lifecycle independent of deliverables,
    though deliverables may reference a workshop (via workshop_id) to indicate
    dependency.

    Multiple consultants can be assigned to a single workshop via the
    workshop_consultants join table.

    Status lifecycle: scheduled -> prep_in_progress -> completed -> cancelled
    """
    __tablename__ = "workshops"

    # Primary key — auto-incrementing integer.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # FK to the parent project. CASCADE delete ensures workshops are removed
    # when their project is deleted.
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))

    # Display name of the workshop (e.g., "Kickoff Meeting", "AC Walkthrough").
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Scheduled date for the workshop session. Null if not yet scheduled.
    workshop_date: Mapped[Date | None] = mapped_column(Date)

    # Current lifecycle status of the workshop.
    # Valid values: scheduled | prep_in_progress | completed | cancelled
    status: Mapped[str] = mapped_column(String(30), default="scheduled")

    # Expected duration of the workshop in hours (e.g., 2.0 for a 2-hour session).
    # Used for capacity planning to account for consultant time.
    duration_hours: Mapped[float | None] = mapped_column(Numeric(6, 2))

    # External ID from Monday.com for this workshop item.
    # Used for delta-matching during synchronization/import.
    monday_item_id: Mapped[str | None] = mapped_column(String(100))

    # Timestamp of when this workshop record was first created.
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # --- Relationships ---

    # Back-reference to the parent project.
    project: Mapped["Project"] = relationship("Project", back_populates="workshops")  # type: ignore

    # Consultants assigned to facilitate or attend this workshop.
    # Uses "selectin" loading for efficient batch-loading.
    consultants: Mapped[list["Consultant"]] = relationship(  # type: ignore
        "Consultant", secondary="workshop_consultants", lazy="selectin"
    )


class DeliverablePhase(Base):
    """
    A single phase within a deliverable's lifecycle.

    Each deliverable can be broken into up to 4 phases, each representing a
    distinct stage of work:
      - workshop: Client interaction / data gathering phase
      - draft: Primary content creation / implementation phase
      - qa: Quality assurance and review phase
      - delivery: Final delivery and client acceptance phase

    Each phase tracks its own date range, total hours, and status independently.
    Phases are linked to assignments (consultant-to-phase mappings) that drive
    the capacity grid and weekly allocation calculations.

    The sort_order field determines the sequential display order of phases
    within a deliverable (typically workshop=0, draft=1, qa=2, delivery=3).
    """
    __tablename__ = "deliverable_phases"

    # Primary key — auto-incrementing integer.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # FK to the parent deliverable. CASCADE delete ensures phases are removed
    # when their deliverable is deleted.
    deliverable_id: Mapped[int] = mapped_column(ForeignKey("deliverables.id", ondelete="CASCADE"))

    # The type/stage of this phase within the deliverable lifecycle.
    # Valid values: workshop | draft | qa | delivery
    phase_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # Planned or actual start date for this phase.
    start_date: Mapped[Date | None] = mapped_column(Date)

    # Planned or actual end date for this phase.
    end_date: Mapped[Date | None] = mapped_column(Date)

    # Total hours allocated to this phase. Distributed across assignments
    # and subsequently broken into weekly allocations.
    total_hours: Mapped[float | None] = mapped_column(Numeric(6, 2))

    # Current status of this phase. Mirrors deliverable-level statuses.
    # Defaults to "not_started".
    status: Mapped[str] = mapped_column(String(30), default="not_started")

    # Display ordering within the parent deliverable.
    # Convention: workshop=0, draft=1, qa=2, delivery=3.
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # --- Relationships ---

    # Back-reference to the parent deliverable.
    deliverable: Mapped["Deliverable"] = relationship(back_populates="phases")

    # Consultant assignments for this phase. A phase can have multiple
    # assignments (e.g., two consultants splitting the drafting work).
    # Cascade delete ensures assignments are removed with the phase.
    assignments: Mapped[list["Assignment"]] = relationship(  # type: ignore
        "Assignment", back_populates="phase", cascade="all, delete-orphan"
    )
