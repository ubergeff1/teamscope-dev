"""
Alerts router — API prefix: /alerts

Manages alert rules and their triggered instances. Alert rules define conditions
(e.g., utilization thresholds, deadline proximity) that are evaluated periodically.
When a rule's condition is met, an AlertInstance is created.

Sub-resources:
  /alerts/rules      — CRUD for alert rule definitions
  /alerts/instances  — Read and acknowledge triggered alert instances

Endpoints:
  GET    /alerts/rules                              — List all alert rules
  POST   /alerts/rules                              — Create a new alert rule
  PATCH  /alerts/rules/{rule_id}                    — Update an alert rule
  DELETE /alerts/rules/{rule_id}                    — Delete an alert rule
  GET    /alerts/instances                           — List alert instances (optionally by status)
  POST   /alerts/instances/{instance_id}/acknowledge — Acknowledge an alert instance
"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import get_db
from app.models.alert import AlertRule, AlertInstance
from app.schemas.alert import AlertRuleCreate, AlertRuleUpdate, AlertRuleOut, AlertInstanceOut
from app.utils.auth import get_current_user

# Router setup: all endpoints prefixed with /alerts, grouped under "alerts" tag
router = APIRouter(prefix="/alerts", tags=["alerts"])
# Type aliases for dependency injection
Auth = Annotated[str, Depends(get_current_user)]
DB = Annotated[Session, Depends(get_db)]


# ── Rules ─────────────────────────────────────────────────────────────────────

@router.get("/rules", response_model=list[AlertRuleOut])
def list_rules(db: DB, _: Auth):
    """GET /alerts/rules — List all alert rules.

    Returns all configured alert rules ordered alphabetically by name.
    """
    return db.query(AlertRule).order_by(AlertRule.name).all()


@router.post("/rules", response_model=AlertRuleOut, status_code=201)
def create_rule(body: AlertRuleCreate, db: DB, _: Auth):
    """POST /alerts/rules — Create a new alert rule.

    Accepts rule configuration (name, condition type, thresholds, etc.)
    in the request body. Returns the created rule with its generated ID.
    """
    rule = AlertRule(**body.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.patch("/rules/{rule_id}", response_model=AlertRuleOut)
def update_rule(rule_id: int, body: AlertRuleUpdate, db: DB, _: Auth):
    """PATCH /alerts/rules/{rule_id} — Partially update an alert rule.

    Only fields included in the request body are updated. Returns the
    updated rule. Returns 404 if the rule is not found.
    """
    rule = db.get(AlertRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", status_code=204)
def delete_rule(rule_id: int, db: DB, _: Auth):
    """DELETE /alerts/rules/{rule_id} — Delete an alert rule.

    Removes the rule and any associated instances (via cascading deletes).
    Returns 204 No Content on success, 404 if the rule is not found.
    """
    rule = db.get(AlertRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    db.delete(rule)
    db.commit()


# ── Instances ─────────────────────────────────────────────────────────────────

@router.get("/instances", response_model=list[AlertInstanceOut])
def list_instances(db: DB, _: Auth, status: str | None = None):
    """GET /alerts/instances — List triggered alert instances.

    Returns the most recent 200 alert instances, ordered by triggered_at
    descending (newest first).

    Query params:
      status (optional): filter instances by status (e.g., "open", "acknowledged")
    """
    q = db.query(AlertInstance).order_by(AlertInstance.triggered_at.desc())
    if status:
        q = q.filter(AlertInstance.status == status)
    # Limit to 200 to prevent excessive response sizes
    return q.limit(200).all()


@router.post("/instances/{instance_id}/acknowledge", response_model=AlertInstanceOut)
def acknowledge_instance(instance_id: int, db: DB, _: Auth):
    """POST /alerts/instances/{instance_id}/acknowledge — Acknowledge an alert instance.

    Marks the alert instance as "acknowledged" and records the current UTC
    timestamp. This indicates that a user has seen and accepted the alert.
    Returns 404 if the instance is not found.
    """
    inst = db.get(AlertInstance, instance_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Alert instance not found")
    # Mark as acknowledged with the current UTC timestamp
    inst.status = "acknowledged"
    inst.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(inst)
    return inst
