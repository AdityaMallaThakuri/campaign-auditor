from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from db.database import get_session
from models.tables import Campaign, AuditSnapshot

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditRunRequest(BaseModel):
    campaign_ids: Optional[list[int]] = None


@router.post("/run")
def run_audit(request: AuditRunRequest = AuditRunRequest(), session: Session = Depends(get_session)):
    from services.smartlead import SmartleadClient
    from services.analyzer import calculate_health_score, diagnose_root_cause, detect_dropoff
    from models.tables import SequenceStep, ReplyCluster

    client = SmartleadClient()

    if request.campaign_ids:
        campaigns = session.exec(
            select(Campaign).where(Campaign.id.in_(request.campaign_ids))
        ).all()
    else:
        campaigns = session.exec(select(Campaign)).all()

    if not campaigns:
        client.sync_campaigns(session)
        campaigns = session.exec(select(Campaign)).all()

    audit_id = f"audit_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    flags = []

    for campaign in campaigns:
        try:
            stats = client.get_campaign_stats(campaign.smartlead_id)
            open_rate = stats.get("open_rate", 0.0)
            reply_rate = stats.get("reply_rate", 0.0)
            bounce_rate = stats.get("bounce_rate", 0.0)

            steps = session.exec(
                select(SequenceStep)
                .where(SequenceStep.campaign_id == campaign.id)
                .order_by(SequenceStep.step_number)
            ).all()
            step_dropoff = detect_dropoff(steps)

            clusters = session.exec(
                select(ReplyCluster).where(ReplyCluster.campaign_id == campaign.id)
            ).all()

            health = calculate_health_score(open_rate, reply_rate, bounce_rate)
            root_cause, detail = diagnose_root_cause(
                open_rate, reply_rate, bounce_rate, step_dropoff, clusters
            )

            snapshot = AuditSnapshot(
                campaign_id=campaign.id,
                open_rate=open_rate,
                reply_rate=reply_rate,
                bounce_rate=bounce_rate,
                health_score=health,
                root_cause=root_cause,
                root_cause_detail=detail,
                step_dropoff=step_dropoff,
            )
            session.add(snapshot)

            flags.append({
                "campaign_id": campaign.id,
                "name": campaign.name,
                "root_cause": root_cause,
                "health_score": health,
            })
        except Exception as e:
            flags.append({
                "campaign_id": campaign.id,
                "name": campaign.name,
                "error": str(e),
            })

    session.commit()
    return {
        "audit_id": audit_id,
        "campaigns_audited": len(campaigns),
        "flags": flags,
    }


@router.get("/history/{campaign_id}")
def audit_history(campaign_id: int, session: Session = Depends(get_session)):
    campaign = session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    snapshots = session.exec(
        select(AuditSnapshot)
        .where(AuditSnapshot.campaign_id == campaign_id)
        .order_by(AuditSnapshot.audited_at.asc())
    ).all()

    return {
        "campaign_id": campaign_id,
        "snapshots": [
            {
                "audited_at": s.audited_at.isoformat(),
                "health_score": s.health_score,
                "open_rate": s.open_rate,
                "reply_rate": s.reply_rate,
                "bounce_rate": s.bounce_rate,
            }
            for s in snapshots
        ],
    }


@router.get("/cross-campaign")
def cross_campaign_intel(session: Session = Depends(get_session)):
    from sqlalchemy import func
    from models.tables import SequenceStep, ReplyCluster

    # Worst step positions by avg reply rate
    steps = session.exec(select(SequenceStep)).all()
    step_agg: dict[int, list[float]] = {}
    for s in steps:
        step_agg.setdefault(s.step_number, []).append(s.reply_rate)

    worst_steps = sorted(
        [
            {
                "step_number": k,
                "avg_reply_rate": round(sum(v) / len(v), 4),
                "campaigns_affected": len(v),
            }
            for k, v in step_agg.items()
        ],
        key=lambda x: x["avg_reply_rate"],
    )[:5]

    # Top reply themes across campaigns
    clusters = session.exec(select(ReplyCluster)).all()
    theme_agg: dict[str, dict] = {}
    for c in clusters:
        cat = c.category
        if cat not in theme_agg:
            theme_agg[cat] = {"count": 0, "campaigns": set()}
        theme_agg[cat]["count"] += c.count
        theme_agg[cat]["campaigns"].add(c.campaign_id)

    top_themes = sorted(
        [
            {
                "theme": k,
                "count": v["count"],
                "campaigns_affected": len(v["campaigns"]),
            }
            for k, v in theme_agg.items()
        ],
        key=lambda x: x["count"],
        reverse=True,
    )[:5]

    # Best subject styles (based on open rates per step)
    style_agg: dict[str, list[float]] = {}
    for s in steps:
        if s.subject:
            subject = s.subject.lower()
            if "?" in subject:
                style = "question"
            elif any(c.isdigit() for c in subject[:10]):
                style = "number_lead"
            elif subject.startswith("re:") or subject.startswith("fwd:"):
                style = "reply_thread"
            else:
                style = "statement"
            style_agg.setdefault(style, []).append(s.open_rate)

    best_subjects = sorted(
        [
            {"style": k, "avg_open_rate": round(sum(v) / len(v), 4)}
            for k, v in style_agg.items()
        ],
        key=lambda x: x["avg_open_rate"],
        reverse=True,
    )

    return {
        "best_subject_styles": best_subjects,
        "top_reply_themes": top_themes,
        "worst_step_positions": worst_steps,
    }
