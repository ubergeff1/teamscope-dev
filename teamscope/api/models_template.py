"""
Template models — reusable project and deliverable blueprints.
ProjectTemplate defines a standard set of deliverables for a framework/impact level combo.
DeliverableTemplate defines a single reusable deliverable within a project template.
WorkshopTemplate defines a single reusable workshop within a project template.
"""
from sqlalchemy import Integer, String, Text, Numeric, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base


class ProjectTemplate(Base):
    __tablename__ = "project_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    framework_id: Mapped[int | None] = mapped_column(ForeignKey("frameworks.id"))
    impact_level_id: Mapped[int | None] = mapped_column(ForeignKey("impact_levels.id"))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    deliverable_templates: Mapped[list["DeliverableTemplate"]] = relationship(
        back_populates="project_template", cascade="all, delete-orphan"
    )
    workshop_templates: Mapped[list["WorkshopTemplate"]] = relationship(
        back_populates="project_template", cascade="all, delete-orphan",
        order_by="WorkshopTemplate.sort_order"
    )
    framework: Mapped["Framework | None"] = relationship("Framework")  # type: ignore
    impact_level: Mapped["ImpactLevel | None"] = relationship("ImpactLevel")  # type: ignore


class DeliverableTemplate(Base):
    __tablename__ = "deliverable_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_template_id: Mapped[int] = mapped_column(ForeignKey("project_templates.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # control_family | appendix | workshop | flat_hours | custom
    deliverable_type: Mapped[str] = mapped_column(String(20), nullable=False)
    control_family_code: Mapped[str | None] = mapped_column(String(10))
    default_hours_per_control: Mapped[float | None] = mapped_column(Numeric(5, 2))
    default_flat_hours: Mapped[float | None] = mapped_column(Numeric(6, 2))   # consultant hours
    default_qa_hours: Mapped[float | None] = mapped_column(Numeric(6, 2))
    default_business_days: Mapped[int | None] = mapped_column(Integer)
    workshop_template_id: Mapped[int | None] = mapped_column(ForeignKey("workshop_templates.id", ondelete="SET NULL"))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    project_template: Mapped["ProjectTemplate"] = relationship(back_populates="deliverable_templates")


class WorkshopTemplate(Base):
    __tablename__ = "workshop_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_template_id: Mapped[int] = mapped_column(ForeignKey("project_templates.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    duration_hours: Mapped[float | None] = mapped_column(Numeric(5, 2))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    project_template: Mapped["ProjectTemplate"] = relationship(back_populates="workshop_templates")
