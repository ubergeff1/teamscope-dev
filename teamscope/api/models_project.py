"""
Project model — represents a client engagement.
Links to a framework and impact level to determine which control families apply.
monday_project_id stores the external ID used for delta-matching on re-import.
color is auto-assigned from the palette and can be overridden by the user.
"""
from sqlalchemy import Integer, String, Text, Date, Boolean, ForeignKey, DateTime, Table, Column, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base


project_consultants = Table(
    "project_consultants",
    Base.metadata,
    Column("project_id", Integer, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("consultant_id", Integer, ForeignKey("consultants.id", ondelete="CASCADE"), primary_key=True),
)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    client_name: Mapped[str | None] = mapped_column(String(200))
    framework_id: Mapped[int | None] = mapped_column(ForeignKey("frameworks.id"))
    impact_level_id: Mapped[int | None] = mapped_column(ForeignKey("impact_levels.id"))
    start_date: Mapped[Date | None] = mapped_column(Date)
    end_date: Mapped[Date | None] = mapped_column(Date)
    # active | on_hold | complete | archived
    status: Mapped[str] = mapped_column(String(30), default="active")
    monday_project_id: Mapped[str | None] = mapped_column(String(100))
    color: Mapped[str] = mapped_column(String(7), default="#4C9BE8")
    notes: Mapped[str | None] = mapped_column(Text)
    budgeted_hours: Mapped[float | None] = mapped_column(Numeric(8, 2))
    snap_end_to_friday: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    framework: Mapped["Framework | None"] = relationship("Framework")  # type: ignore
    impact_level: Mapped["ImpactLevel | None"] = relationship("ImpactLevel")  # type: ignore
    deliverables: Mapped[list["Deliverable"]] = relationship(  # type: ignore
        "Deliverable", back_populates="project", cascade="all, delete-orphan"
    )
    workshops: Mapped[list["Workshop"]] = relationship(  # type: ignore
        "Workshop", back_populates="project", cascade="all, delete-orphan"
    )
    consultants: Mapped[list["Consultant"]] = relationship(  # type: ignore
        "Consultant", secondary="project_consultants", lazy="selectin"
    )
