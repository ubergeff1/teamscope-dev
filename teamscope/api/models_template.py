"""
Template models — reusable project and deliverable blueprints.

This module defines the template system that allows users to create standardized
project configurations for common engagement types. When a new project is created
from a template, the template's deliverables and workshops are cloned into the
project with their default settings.

ProjectTemplate: Defines a standard set of deliverables and workshops for a given
  framework/impact level combination (e.g., "FedRAMP Moderate Standard Package").

DeliverableTemplate: A single reusable deliverable blueprint within a project
  template, specifying default hours, type, and control family mapping.

WorkshopTemplate: A single reusable workshop blueprint within a project template,
  specifying default name and duration.
"""
from sqlalchemy import Integer, String, Text, Numeric, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base


class ProjectTemplate(Base):
    """
    A reusable blueprint for creating new projects with pre-configured deliverables
    and workshops.

    Project templates capture the typical structure of an engagement for a given
    framework and impact level. When instantiated, all child deliverable templates
    and workshop templates are cloned into the new project, saving setup time and
    ensuring consistency across similar engagements.

    Templates are independent of actual projects — they serve as read-only
    blueprints that can be versioned and updated without affecting previously
    created projects.
    """
    __tablename__ = "project_templates"

    # Primary key — auto-incrementing integer.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Human-readable template name (e.g., "FedRAMP Moderate Standard").
    # Max 100 characters; required field.
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # FK to the compliance framework this template is designed for.
    # Optional — a template may be framework-agnostic.
    framework_id: Mapped[int | None] = mapped_column(ForeignKey("frameworks.id"))

    # FK to the impact level within the framework. Together with framework_id,
    # determines which control families and default hours apply.
    impact_level_id: Mapped[int | None] = mapped_column(ForeignKey("impact_levels.id"))

    # Optional description explaining when to use this template, what it includes,
    # or any special considerations.
    description: Mapped[str | None] = mapped_column(Text)

    # Timestamp of when this template was first created.
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # --- Relationships ---

    # All deliverable blueprints belonging to this template. Cascade delete
    # ensures child templates are removed when the parent is deleted.
    deliverable_templates: Mapped[list["DeliverableTemplate"]] = relationship(
        back_populates="project_template", cascade="all, delete-orphan"
    )

    # All workshop blueprints belonging to this template. Cascade delete
    # ensures child templates are removed when the parent is deleted.
    # Ordered by sort_order for consistent sequencing.
    workshop_templates: Mapped[list["WorkshopTemplate"]] = relationship(
        back_populates="project_template", cascade="all, delete-orphan",
        order_by="WorkshopTemplate.sort_order"
    )

    # The compliance framework this template is designed for (e.g., FedRAMP).
    framework: Mapped["Framework | None"] = relationship("Framework")  # type: ignore

    # The impact level within the framework (e.g., Moderate).
    impact_level: Mapped["ImpactLevel | None"] = relationship("ImpactLevel")  # type: ignore


class DeliverableTemplate(Base):
    """
    A reusable deliverable blueprint within a project template.

    Stores default configuration values that will be applied when a new project
    is instantiated from the parent ProjectTemplate. The control_family_code
    field stores the code (e.g., "AC") rather than a FK, allowing templates to
    be resolved against different impact levels at instantiation time.
    """
    __tablename__ = "deliverable_templates"

    # Primary key — auto-incrementing integer.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # FK to the parent project template. CASCADE delete ensures deliverable
    # templates are removed when their project template is deleted.
    project_template_id: Mapped[int] = mapped_column(ForeignKey("project_templates.id", ondelete="CASCADE"))

    # Default display name for the deliverable (e.g., "AC - Access Control").
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Deliverable type that will be set on the instantiated deliverable.
    # Valid values: control_family | appendix | workshop | flat_hours | custom
    deliverable_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # Control family code (e.g., "AC", "AU", "CA") used to look up the
    # matching ControlFamily record at project instantiation time.
    # Only applicable when deliverable_type is "control_family". Stored as a
    # code rather than FK so templates can be reused across impact levels.
    control_family_code: Mapped[str | None] = mapped_column(String(10))

    # Default hours per control for control_family type deliverables.
    # Multiplied by the actual control_count from the resolved ControlFamily.
    default_hours_per_control: Mapped[float | None] = mapped_column(Numeric(5, 2))

    # Default flat consultant hours for flat_hours/appendix/custom types.
    default_flat_hours: Mapped[float | None] = mapped_column(Numeric(6, 2))   # consultant hours

    # Default QA/review hours allocated for this deliverable.
    default_qa_hours: Mapped[float | None] = mapped_column(Numeric(6, 2))

    # Default number of business days for the drafting phase.
    # Used by the auto-scheduler when instantiating from template.
    default_business_days: Mapped[int | None] = mapped_column(Integer)

    # FK to an optional associated workshop template. SET NULL on workshop
    # template deletion so the deliverable template survives independently.
    workshop_template_id: Mapped[int | None] = mapped_column(ForeignKey("workshop_templates.id", ondelete="SET NULL"))

    # Display ordering within the parent project template.
    # Lower values appear first.
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # --- Relationships ---

    # Back-reference to the parent project template.
    project_template: Mapped["ProjectTemplate"] = relationship(back_populates="deliverable_templates")


class WorkshopTemplate(Base):
    """
    A reusable workshop blueprint within a project template.

    Stores default name and duration for workshops that will be created when
    a project is instantiated from the parent ProjectTemplate. Workshop templates
    are referenced by DeliverableTemplates via workshop_template_id to establish
    phase dependencies.
    """
    __tablename__ = "workshop_templates"

    # Primary key — auto-incrementing integer.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # FK to the parent project template. CASCADE delete ensures workshop
    # templates are removed when their project template is deleted.
    project_template_id: Mapped[int] = mapped_column(ForeignKey("project_templates.id", ondelete="CASCADE"))

    # Default display name for the workshop (e.g., "Kickoff Meeting").
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Default duration in hours for this workshop session.
    duration_hours: Mapped[float | None] = mapped_column(Numeric(5, 2))

    # Display ordering within the parent project template.
    # Lower values appear first.
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # --- Relationships ---

    # Back-reference to the parent project template.
    project_template: Mapped["ProjectTemplate"] = relationship(back_populates="workshop_templates")
