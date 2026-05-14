from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import get_db
from app.models.alert import AlertRule, AlertInstance
from app.schemas.alert import AlertRuleCreate, AlertRuleUpdate, AlertRuleOut, AlertInstanceOut
from app.utils.auth import get_current_user

router = APIRouter(prefix="/alerts", tags=["alerts"])
Auth = Annotated[str, Depends(get_current_user)]
DB = Annotated[Session, Depends(get_db)]


# ── Rules ─────────────────────────────────────────────────────────────────────

@router.get("/rules", response_model=list[AlertRuleOut])
def list_rules(db: DB, _: Auth):
    return db.query(AlertRule).order_by(AlertRule.name).all()


@router.post("/rules", response_model=AlertRuleOut, status_code=201)
def create_rule(body: AlertRuleCreate, db: DB, _: Auth):
    rule = AlertRule(**body.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.patch("/rules/{rule_id}", response_model=AlertRuleOut)
def update_rule(rule_id: int, body: AlertRuleUpdate, db: DB, _: Auth):
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
    rule = db.get(AlertRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    db.delete(rule)
    db.commit()


# ── Instances ─────────────────────────────────────────────────────────────────

@router.get("/instances", response_model=list[AlertInstanceOut])
def list_instances(db: DB, _: Auth, status: str | None = None):
    q = db.query(AlertInstance).order_by(AlertInstance.triggered_at.desc())
    if status:
        q = q.filter(AlertInstance.status == status)
    return q.limit(200).all()


@router.post("/instances/{instance_id}/acknowledge", response_model=AlertInstanceOut)
def acknowledge_instance(instance_id: int, db: DB, _: Auth):
    inst = db.get(AlertInstance, instance_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Alert instance not found")
    inst.status = "acknowledged"
    inst.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(inst)
    return inst
