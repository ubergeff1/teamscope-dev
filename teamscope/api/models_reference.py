"""
Reference / seed data models — frameworks, impact levels, and control families.

This module defines the compliance reference data that underpins TeamScope's
project and deliverable structure. These entities form a three-level hierarchy:

  Framework (e.g., FedRAMP, GovRAMP, CMMC)
    -> ImpactLevel (e.g., Low, Moderate, High for FedRAMP; L1, L2, L3 for CMMC)
      -> ControlFamily (e.g., AC - Access Control with 25 controls)

This data is pre-populated by the database seed script (database/init/01_seed.sql)
and is treated as read-only within the application. It provides the foundation for:
- Determining which control families apply to a project based on its framework
  and impact level selection.
- Calculating deliverable hours for control_family type deliverables
  (control_count * hours_per_control).
- Populating dropdowns and reference lookups in the UI.
"""
from sqlalchemy import Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Framework(Base):
    """
    A compliance framework that governs the structure of a consulting engagement.

    Frameworks represent top-level regulatory or certification standards such as
    FedRAMP, GovRAMP, or CMMC. Each framework has one or more impact levels,
    which in turn define the set of applicable control families.

    This is seed data — records are created during database initialization and
    are not modified through the application UI.
    """
    __tablename__ = "frameworks"

    # Primary key — auto-incrementing integer.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Short name of the framework. Must be unique across all frameworks.
    # Examples: "FedRAMP", "GovRAMP", "CMMC"
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # FedRAMP, GovRAMP, CMMC

    # Optional longer description of the framework, its purpose, or applicability.
    description: Mapped[str | None] = mapped_column(Text)

    # --- Relationships ---

    # All impact levels defined within this framework.
    impact_levels: Mapped[list["ImpactLevel"]] = relationship(back_populates="framework")


class ImpactLevel(Base):
    """
    A classification tier within a framework that determines control scope.

    Impact levels represent the severity or sensitivity classification within a
    framework. For example, FedRAMP defines Low, Moderate, and High impact levels,
    each with a different number and set of control families.

    The combination of (framework_id, name) is unique — each framework has its
    own distinct set of impact level names.

    This is seed data — records are created during database initialization.
    """
    __tablename__ = "impact_levels"

    # Unique constraint ensures no duplicate impact level names within a framework.
    __table_args__ = (UniqueConstraint("framework_id", "name"),)

    # Primary key — auto-incrementing integer.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # FK to the parent framework this impact level belongs to.
    framework_id: Mapped[int] = mapped_column(ForeignKey("frameworks.id"))

    # Short name of the impact level within its framework.
    # Examples: "Low", "Moderate", "High" (FedRAMP); "L1", "L2", "L3" (CMMC)
    name: Mapped[str] = mapped_column(String(20), nullable=False)  # Low, Moderate, High, L1, L2, L3

    # --- Relationships ---

    # Back-reference to the parent framework.
    framework: Mapped["Framework"] = relationship(back_populates="impact_levels")

    # All control families applicable at this impact level.
    control_families: Mapped[list["ControlFamily"]] = relationship(back_populates="impact_level")


class ControlFamily(Base):
    """
    A group of related security controls within an impact level.

    Control families represent logical groupings of security controls as defined
    by the framework (e.g., AC = Access Control, AU = Audit and Accountability).
    Each family has a specific number of controls (control_count) that determines
    the effort required for control_family type deliverables.

    When a project selects a framework and impact level, the applicable control
    families are used to generate deliverables. The control_count field is
    multiplied by the deliverable's hours_per_control to calculate total hours.

    The combination of (impact_level_id, code) is unique — each impact level
    has its own set of control family codes.

    This is seed data — records are created during database initialization.
    """
    __tablename__ = "control_families"

    # Unique constraint ensures no duplicate control family codes within an impact level.
    __table_args__ = (UniqueConstraint("impact_level_id", "code"),)

    # Primary key — auto-incrementing integer.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # FK to the impact level this control family belongs to.
    impact_level_id: Mapped[int] = mapped_column(ForeignKey("impact_levels.id"))

    # Short code identifying the control family (e.g., "AC", "AU", "CA", "CM").
    # Used for display, sorting, and matching with DeliverableTemplate.control_family_code.
    code: Mapped[str] = mapped_column(String(10), nullable=False)   # AC, AU, CA, etc.

    # Full descriptive name of the control family
    # (e.g., "Access Control", "Audit and Accountability").
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Number of individual controls in this family at this impact level.
    # Drives hour calculations: deliverable.total_hours = control_count * hours_per_control.
    control_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # --- Relationships ---

    # Back-reference to the parent impact level.
    impact_level: Mapped["ImpactLevel"] = relationship(back_populates="control_families")
