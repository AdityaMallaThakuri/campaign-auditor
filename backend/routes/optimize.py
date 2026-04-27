from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import Optional
from pydantic import BaseModel

from db.database import get_session
from models.tables import Campaign, AuditSnapshot, SequenceStep, AIRewrite, ReplyCluster

router = APIRouter(prefix="/optimize", tags=["optimize"])


class DiagnoseRequest(BaseModel):
    campaign_id: int


class RewriteRequest(BaseModel):
    campaign_id: int
    step_id: int
    instruction: Optional[str] = None


@router.post("/diagnose")
def diagnose(request: DiagnoseRequest, session: Session = Depends(get_session)):
    from services.claude import diagnose_campaign

    campaign = session.get(Campaign, request.campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    latest_audit = session.exec(
        select(AuditSnapshot)
        .where(AuditSnapshot.campaign_id == request.campaign_id)
        .order_by(AuditSnapshot.audited_at.desc())
    ).first()

    clusters = session.exec(
        select(ReplyCluster).where(ReplyCluster.campaign_id == request.campaign_id)
    ).all()

    result = diagnose_campaign(campaign, latest_audit, clusters)
    return {"campaign_id": request.campaign_id, **result}


@router.post("/rewrite")
def rewrite(request: RewriteRequest, session: Session = Depends(get_session)):
    from services.claude import rewrite_step as claude_rewrite

    campaign = session.get(Campaign, request.campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    step = session.get(SequenceStep, request.step_id)
    if not step or step.campaign_id != request.campaign_id:
        raise HTTPException(status_code=404, detail="Step not found")

    result = claude_rewrite(step, campaign, request.instruction)

    record = AIRewrite(
        step_id=step.id,
        campaign_id=campaign.id,
        original_copy=step.body,
        rewritten_copy=result.get("rewrite"),
        suggestions=result.get("subject_alternatives", []),
        model_used="claude-sonnet-4-5",
    )
    session.add(record)
    session.commit()

    return {
        "step_id": step.id,
        "step_number": step.step_number,
        "original": step.body,
        **result,
    }


@router.get("/rewrites/{campaign_id}")
def get_rewrites(campaign_id: int, session: Session = Depends(get_session)):
    campaign = session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    rewrites = session.exec(
        select(AIRewrite, SequenceStep)
        .join(SequenceStep, AIRewrite.step_id == SequenceStep.id)
        .where(AIRewrite.campaign_id == campaign_id)
        .order_by(AIRewrite.generated_at.desc())
    ).all()

    return {
        "campaign_id": campaign_id,
        "rewrites": [
            {
                "id": r.id,
                "step_number": s.step_number,
                "original": r.original_copy,
                "rewrite": r.rewritten_copy,
                "suggestions": r.suggestions,
                "model_used": r.model_used,
                "generated_at": r.generated_at.isoformat(),
            }
            for r, s in rewrites
        ],
    }
