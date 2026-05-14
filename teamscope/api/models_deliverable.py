"""
Deliverable, Workshop, and DeliverablePhase models.

Deliverable: A documentation task (e.g. AC control family implementation).
  - control_family type: total_hours = control_count * hours_per_control
  - flat_hours type: total_hours = flat_hours

Workshop: A scheduled session with a client. Uses a separate status set.

DeliverablePhase: Each deliverable goes through up to 4 phases:
  workshop -> draft -> qa -> delivery
  Each phase has its own date range, hours, and consultant assignment.
"""
from sqlalchemy import Integer, String, Text, Numeric, Date, Boolean, ForeignKey, DateTime, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base

workshop_consultants = Table(
    "workshop_consultants",
    Base.metadata,
    Column("workshop_id", Integer, ForeignKey("workshops.id", ondelete="CASCADE"), primary_key=True),
    Column("consultant_id", Integer, ForeignKey("consultants.id", ondelete="CASCADE"), primary_key=True),
)


class Deliverable(Base):
    __tablename__ = "deliverables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # control_family | appendix | workshop | flat_hours | custom
    deliverable_type: Mapped[str] = mapped_column(String(20), nullable=False)
    control_family_id: Mapped[int | None] = mapped_column(ForeignKey("control_families.id"))
    control_count: Mapped[int | None] = mapped_column(Integer)
    hours_per_control: Mapped[float | None] = mapped_column(Numeric(5, 2))
    flat_hours: Mapped[float | None] = mapped_column(Numeric(6, 2))   # consultant hours
    qa_hours: Mapped[float | None] = mapped_column(Numeric(6, 2))
    business_days: Mapped[int | None] = mapped_column(Integer)
    qa_business_days: Mapped[int | None] = mapped_column(Integer)
    workshop_sequential: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")
    qa_sequential: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")
    # not_started | in_progress | in_qa | delivered | complete
    status: Mapped[str] = mapped_column(String(30), default="not_started")
    start_date: Mapped[Date | None] = mapped_column(Date)
    end_date: Mapped[Date | None] = mapped_column(Date)
    workshop_id: Mapped[int | None] = mapped_column(ForeignKey("workshops.id", ondelete="SET NULL"))
    consultant_id: Mapped[int | None] = mapped_column(ForeignKey("consultants.id", ondelete="SET NULL"))
    qa_consultant_id: Mapped[int | None] = mapped_column(ForeignKey("consultants.id", ondelete="SET NULL"))
    monday_item_id: Mapped[str | None] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship("Project", back_populates="deliverables")  # type: ignore
    control_family: Mapped["ControlFamily | None"] = relationship("ControlFamily")  # type: ignore
    phases: Mapped[list["DeliverablePhase"]] = relationship(
        back_populates="deliverable", cascade="all, delete-orphan", order_by="DeliverablePhase.sort_order"
    )

    @property
    def total_planned_hours(self) -> float:
        """Sum of consultant hours and review hours."""
        return float(self.flat_hours or 0) + float(self.qa_hours or 0)


class Workshop(Base):
    __tablename__ = "workshops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    workshop_date: Mapped[Date | None] = mapped_column(Date)
    # scheduled | prep_in_progress | completed | cancelled
    status: Mapped[str] = mapped_column(String(30), default="scheduled")
    duration_hours: Mapped[float | None] = mapped_column(Numeric(6, 2))
    monday_item_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["Project"] = relationship("Project", back_populates="workshops")  # type: ignore
    consultants: Mapped[list["Consultant"]] = relationship(  # type: ignore
        "Consultant", secondary="workshop_consultants", lazy="selectin"
    )


class DeliverablePhase(Base):
    __tablename__ = "deliverable_phases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deliverable_id: Mapped[int] = mapped_column(ForeignKey("deliverables.id", ondelete="CASCADE"))
    # workshop | draft | qa | delivery
    phase_type: Mapped[str] = mapped_column(String(20), nullable=False)
    start_date: Mapped[Date | None] = mapped_column(Date)
    end_date: Mapped[Date | None] = mapped_column(Date)
    total_hours: Mapped[float | None] = mapped_column(Numeric(6, 2))
    status: Mapped[str] = mapped_column(String(30), default="not_started")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    deliverable: Mapped["Deliverable"] = relationship(back_populates="phases")
    assignments: Mapped[list["Assignment"]] = relationship(  # type: ignore
        "Assignment", back_populates="phase", cascade="all, delete-orphan"
    )
