from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import Optional
from datetime import datetime

from db.database import get_session
from models.tables import Campaign, AuditSnapshot

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("")
def list_campaigns(session: Session = Depends(get_session)):
    campaigns = session.exec(select(Campaign)).all()
    result = []
    for c in campaigns:
        latest = session.exec(
            select(AuditSnapshot)
            .where(AuditSnapshot.campaign_id == c.id)
            .order_by(AuditSnapshot.audited_at.desc())
        ).first()
        result.append({
            "id": c.id,
            "smartlead_id": c.smartlead_id,
            "name": c.name,
            "status": c.status,
            "total_leads": c.total_leads,
            "health_score": latest.health_score if latest else None,
            "root_cause": latest.root_cause if latest else None,
            "audited_at": latest.audited_at.isoformat() if latest else None,
            "fetched_at": c.fetched_at.isoformat() if c.fetched_at else None,
        })
    return {"campaigns": result}


@router.get("/{campaign_id}")
def get_campaign(campaign_id: int, session: Session = Depends(get_session)):
    from models.tables import SequenceStep, ReplyCluster

    campaign = session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    latest_audit = session.exec(
        select(AuditSnapshot)
        .where(AuditSnapshot.campaign_id == campaign_id)
        .order_by(AuditSnapshot.audited_at.desc())
    ).first()

    sequences = session.exec(
        select(SequenceStep)
        .where(SequenceStep.campaign_id == campaign_id)
        .order_by(SequenceStep.step_number)
    ).all()

    clusters = session.exec(
        select(ReplyCluster)
        .where(ReplyCluster.campaign_id == campaign_id)
        .order_by(ReplyCluster.count.desc())
    ).all()

    return {
        "campaign": campaign.model_dump(),
        "latest_audit": latest_audit.model_dump() if latest_audit else None,
        "sequences": [s.model_dump() for s in sequences],
        "reply_clusters": [c.model_dump() for c in clusters],
    }


@router.post("/sync")
def sync_campaigns(session: Session = Depends(get_session)):
    from services.smartlead import SmartleadClient

    client = SmartleadClient()
    start = datetime.utcnow()
    synced = client.sync_campaigns(session, force=True)
    duration_ms = int((datetime.utcnow() - start).total_seconds() * 1000)
    return {"synced": synced, "duration_ms": duration_ms}
