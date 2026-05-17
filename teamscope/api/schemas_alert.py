"""
Pydantic schemas for Alert Rule and Alert Instance CRUD operations.

These schemas validate request/response data for the /alerts API endpoints.
They correspond to the following SQLAlchemy models defined in
``models_alert.py``:
    - ``AlertRule``      (table: ``alert_rules``)
    - ``AlertInstance``   (table: ``alert_instances``)

The alerting subsystem proactively notifies users about capacity issues,
budget risks, and scheduling gaps.  Alert rules define the conditions to
monitor, and alert instances represent specific fired occurrences of those
rules.

Alert rule types and their configurations:
    - overallocation:          {"threshold_pct": 90, "consecutive_weeks": 2}
    - underallocation:         {"threshold_pct": 30, "consecutive_weeks": 2}
    - budget_threshold:        {"threshold_pct": 90}
    - unassigned_deliverable:  {"days_warning": 14}
    - custom:                  User-defined (future extensibility)

Alert instance lifecycle: active -> acknowledged -> resolved

Schema pattern:
    - AlertRuleCreate     -- POST /alerts/rules  (required fields + defaults)
    - AlertRuleUpdate     -- PATCH /alerts/rules/{id}  (all fields optional)
    - AlertRuleOut        -- Response body for rule endpoints
    - AlertInstanceOut    -- Response body for instance endpoints (read-only)
"""
from datetime import datetime
from pydantic import BaseModel, Field


class AlertRuleCreate(BaseModel):
    """Schema for creating a new alert rule (POST /alerts/rules).

    Both ``name`` and ``rule_type`` are required.  The ``rule_config`` JSON
    string containing threshold parameters can be set at creation or added
    later via update.

    Corresponds to the ``AlertRule`` SQLAlchemy model (table: ``alert_rules``).
    """
    # Human-readable name describing the rule; required, max 150 characters.
    # Example: "Over 90% capacity alert", "Budget exhaustion warning".
    name: str = Field(..., max_length=150)
    # Category of condition to monitor; required.
    # Must be one of: overallocation | underallocation | budget_threshold |
    # unassigned_deliverable | custom
    rule_type: str = Field(
        ..., pattern=r"^(overallocation|underallocation|budget_threshold|unassigned_deliverable|custom)$"
    )
    # JSON-encoded configuration with threshold parameters.
    # Structure depends on rule_type (see module docstring for examples).
    # Optional -- can be set later via update.
    rule_config: str | None = None  # JSON string
    # Whether the rule is actively evaluated by the background worker.
    # Defaults to True so new rules are immediately active.
    is_active: bool = True


class AlertRuleUpdate(BaseModel):
    """Schema for partially updating an alert rule
    (PATCH /alerts/rules/{id}).

    All fields are optional; only non-None values are applied.

    Corresponds to the ``AlertRule`` SQLAlchemy model (table: ``alert_rules``).
    """
    # Updated rule name; max 150 characters. None = keep current value.
    name: str | None = Field(None, max_length=150)
    # Updated rule type. None = keep current value.
    # Note: changing rule_type may require updating rule_config to match.
    rule_type: str | None = None
    # Updated JSON configuration string. None = keep current value.
    rule_config: str | None = None
    # Updated active status. None = keep current value.
    # Setting to False disables evaluation without deleting the rule.
    is_active: bool | None = None


class AlertRuleOut(BaseModel):
    """Response schema for alert rule endpoints.

    Mirrors the ``alert_rules`` table columns.  Excludes internal timestamps
    (created_at, updated_at) and the ``instances`` relationship -- use the
    /alerts/instances endpoint to query fired alerts.

    ``from_attributes = True`` enables direct construction from a SQLAlchemy
    ``AlertRule`` ORM instance.
    """
    # Auto-generated primary key.
    id: int
    # Human-readable rule name.
    name: str
    # Rule type: overallocation | underallocation | budget_threshold |
    # unassigned_deliverable | custom.
    rule_type: str
    # JSON-encoded threshold configuration, if set.
    rule_config: str | None
    # Whether the rule is currently active and being evaluated.
    is_active: bool

    model_config = {"from_attributes": True}


class AlertInstanceOut(BaseModel):
    """Response schema for alert instance endpoints (read-only).

    Represents a specific fired occurrence of an alert rule, tied to the
    entity (consultant, project, or deliverable) that triggered it.

    Alert instances are created by the background worker and managed via
    acknowledge/resolve actions.  There is no Create schema because
    instances are system-generated, not user-created.

    Instance lifecycle: active -> acknowledged -> resolved

    ``from_attributes = True`` enables direct construction from a SQLAlchemy
    ``AlertInstance`` ORM instance.
    """
    # Auto-generated primary key.
    id: int
    # FK to the alert rule that produced this instance.
    rule_id: int
    # FK to the consultant involved (e.g., the over-allocated person). Null if N/A.
    consultant_id: int | None
    # FK to the project involved (e.g., the over-budget project). Null if N/A.
    project_id: int | None
    # FK to the deliverable involved (e.g., the unassigned one). Null if N/A.
    deliverable_id: int | None
    # Human-readable description of what triggered this alert.
    # Generated by the worker with specific details (names, dates, percentages).
    message: str
    # Current lifecycle status: active | acknowledged | resolved.
    status: str
    # Timestamp when this alert was first triggered/created.
    triggered_at: datetime
    # Timestamp when a user acknowledged this alert; null if not yet acknowledged.
    acknowledged_at: datetime | None
    # Timestamp when this alert was resolved (cleared or dismissed); null if still open.
    resolved_at: datetime | None

    model_config = {"from_attributes": True}
