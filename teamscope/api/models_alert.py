"""
Alert models.

AlertRule: A user-configured threshold that triggers notifications.
  Examples:
    - consultant over 90% capacity for 2+ consecutive weeks
    - project budget hours within 10% of total planned hours
    - deliverable has no assignment and start_date is within 2 weeks

AlertInstance: A fired instance of an AlertRule.
  status: active (unfired/ongoing) | acknowledged | resolved
  The worker process creates new instances and resolves old ones on each run.
"""
from sqlalchemy import Integer, String, Text, Numeric, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    # overallocation | underallocation | budget_threshold | unassigned_deliverable | custom
    rule_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # JSON config — keys depend on rule_type:
    #   overallocation: {"threshold_pct": 90, "consecutive_weeks": 2}
    #   budget_threshold: {"threshold_pct": 90}
    #   unassigned_deliverable: {"days_warning": 14}
    rule_config: Mapped[str | None] = mapped_column(Text)  # JSON string
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    instances: Mapped[list["AlertInstance"]] = relationship(
        back_populates="rule", cascade="all, delete-orphan"
    )


class AlertInstance(Base):
    __tablename__ = "alert_instances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("alert_rules.id", ondelete="CASCADE"))
    # Context: which consultant/project triggered the alert (nullable — may not apply)
    consultant_id: Mapped[int | None] = mapped_column(ForeignKey("consultants.id", ondelete="SET NULL"))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"))
    deliverable_id: Mapped[int | None] = mapped_column(ForeignKey("deliverables.id", ondelete="SET NULL"))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    # active | acknowledged | resolved
    status: Mapped[str] = mapped_column(String(20), default="active")
    triggered_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    acknowledged_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))

    rule: Mapped["AlertRule"] = relationship(back_populates="instances")
    consultant: Mapped["Consultant | None"] = relationship("Consultant")  # type: ignore
    project: Mapped["Project | None"] = relationship("Project")  # type: ignore
    deliverable: Mapped["Deliverable | None"] = relationship("Deliverable")  # type: ignore
