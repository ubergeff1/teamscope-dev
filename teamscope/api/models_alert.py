"""
Alert models.

This module defines the alerting subsystem of TeamScope, which proactively
notifies users about capacity issues, budget risks, and scheduling gaps:

AlertRule: A user-configured threshold or condition that triggers notifications.
  Rules are evaluated periodically by a background worker process. Examples:
    - Consultant over 90% capacity for 2+ consecutive weeks (overallocation)
    - Project budget hours within 10% of total planned hours (budget_threshold)
    - Deliverable has no assignment and start_date is within 2 weeks (unassigned_deliverable)

AlertInstance: A specific fired occurrence of an AlertRule, tied to the entity
  (consultant, project, or deliverable) that triggered it.
  Status lifecycle: active -> acknowledged -> resolved
  The worker process creates new instances when conditions are met and
  automatically resolves them when conditions clear.
"""
from sqlalchemy import Integer, String, Text, Numeric, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base


class AlertRule(Base):
    """
    A configurable alert threshold that defines when notifications should fire.

    Alert rules specify the type of condition to monitor, the threshold parameters,
    and whether the rule is currently active. The background worker evaluates all
    active rules on each run and creates or resolves AlertInstance records accordingly.

    The rule_config field stores type-specific parameters as a JSON string:
    - overallocation: {"threshold_pct": 90, "consecutive_weeks": 2}
      Fires when a consultant's weekly utilization exceeds threshold_pct for
      the specified number of consecutive weeks.
    - underallocation: {"threshold_pct": 30, "consecutive_weeks": 2}
      Fires when a consultant's utilization falls below threshold_pct.
    - budget_threshold: {"threshold_pct": 90}
      Fires when actual hours reach threshold_pct of the project's budgeted_hours.
    - unassigned_deliverable: {"days_warning": 14}
      Fires when a deliverable has no consultant assignment and its start_date
      is within days_warning days from today.
    - custom: Arbitrary user-defined conditions (future extensibility).
    """
    __tablename__ = "alert_rules"

    # Primary key — auto-incrementing integer.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Human-readable name describing what this rule monitors
    # (e.g., "Over 90% capacity alert", "Budget exhaustion warning").
    name: Mapped[str] = mapped_column(String(150), nullable=False)

    # The category of condition this rule evaluates.
    # Valid values: overallocation | underallocation | budget_threshold | unassigned_deliverable | custom
    rule_type: Mapped[str] = mapped_column(String(30), nullable=False)

    # JSON-encoded configuration object containing threshold parameters.
    # Structure depends on rule_type (see class docstring for examples).
    # Stored as a JSON string in a Text column rather than a native JSON type
    # for database portability.
    rule_config: Mapped[str | None] = mapped_column(Text)  # JSON string

    # Whether this rule is currently being evaluated by the background worker.
    # Inactive rules are ignored during evaluation but preserved for re-enabling.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamp of when this rule was first created.
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Timestamp of the last modification to this rule's configuration.
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # --- Relationships ---

    # All alert instances that have been fired by this rule.
    # Cascade delete ensures instances are removed when the rule is deleted.
    instances: Mapped[list["AlertInstance"]] = relationship(
        back_populates="rule", cascade="all, delete-orphan"
    )


class AlertInstance(Base):
    """
    A specific fired occurrence of an alert rule.

    Each instance represents a single alert event tied to the entities that
    triggered it (consultant, project, and/or deliverable). Instances are
    created by the background worker when an AlertRule's conditions are met.

    Status lifecycle:
    - active: The alert condition is currently met and has not been acknowledged.
    - acknowledged: A user has seen and acknowledged the alert but the condition
      may still be present.
    - resolved: The condition has cleared (either automatically by the worker
      or manually by a user).

    The worker process manages the lifecycle:
    - On each evaluation run, it creates new "active" instances for newly
      detected conditions.
    - It automatically resolves instances whose conditions have cleared.
    - Users can manually acknowledge or resolve instances via the UI.
    """
    __tablename__ = "alert_instances"

    # Primary key — auto-incrementing integer.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # FK to the alert rule that produced this instance.
    # CASCADE delete ensures instances are removed when their rule is deleted.
    rule_id: Mapped[int] = mapped_column(ForeignKey("alert_rules.id", ondelete="CASCADE"))

    # FK to the consultant who triggered the alert (e.g., the over-allocated person).
    # Nullable — not all alert types involve a specific consultant.
    # SET NULL on consultant deletion preserves the alert history.
    consultant_id: Mapped[int | None] = mapped_column(ForeignKey("consultants.id", ondelete="SET NULL"))

    # FK to the project that triggered the alert (e.g., the over-budget project).
    # Nullable — not all alert types involve a specific project.
    # SET NULL on project deletion preserves the alert history.
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"))

    # FK to the deliverable that triggered the alert (e.g., the unassigned one).
    # Nullable — not all alert types involve a specific deliverable.
    # SET NULL on deliverable deletion preserves the alert history.
    deliverable_id: Mapped[int | None] = mapped_column(ForeignKey("deliverables.id", ondelete="SET NULL"))

    # Human-readable description of what triggered this alert.
    # Generated by the worker process with specific details
    # (e.g., "Jane Doe is at 110% capacity for weeks of Jan 6 and Jan 13").
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Current lifecycle status of this alert instance.
    # Valid values: active | acknowledged | resolved
    status: Mapped[str] = mapped_column(String(20), default="active")

    # Timestamp of when this alert instance was first created/triggered.
    triggered_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Timestamp of when a user acknowledged this alert. Null if not yet acknowledged.
    acknowledged_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))

    # Timestamp of when this alert was resolved (condition cleared or manually dismissed).
    # Null if the alert is still active or only acknowledged.
    resolved_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))

    # --- Relationships ---

    # Back-reference to the parent alert rule.
    rule: Mapped["AlertRule"] = relationship(back_populates="instances")

    # The consultant involved in this alert (if applicable).
    consultant: Mapped["Consultant | None"] = relationship("Consultant")  # type: ignore

    # The project involved in this alert (if applicable).
    project: Mapped["Project | None"] = relationship("Project")  # type: ignore

    # The deliverable involved in this alert (if applicable).
    deliverable: Mapped["Deliverable | None"] = relationship("Deliverable")  # type: ignore
