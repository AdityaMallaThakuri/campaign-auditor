from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from db.database import get_session
from models.tables import Campaign, ReplyCluster

router = APIRouter(prefix="/replies", tags=["replies"])


@router.get("/{campaign_id}/clusters")
def get_clusters(campaign_id: int, session: Session = Depends(get_session)):
    campaign = session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    clusters = session.exec(
        select(ReplyCluster)
        .where(ReplyCluster.campaign_id == campaign_id)
        .order_by(ReplyCluster.count.desc())
    ).all()

    total = sum(c.count for c in clusters)

    return {
        "campaign_id": campaign_id,
        "total_replies": total,
        "clusters": [
            {
                "category": c.category,
                "count": c.count,
                "percentage": c.percentage,
                "themes": c.themes or [],
                "samples": c.sample_replies or [],
            }
            for c in clusters
        ],
    }


@router.post("/{campaign_id}/recluster")
def recluster(campaign_id: int, session: Session = Depends(get_session)):
    from services.smartlead import SmartleadClient
    from services.sentiment import cluster_replies

    campaign = session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    client = SmartleadClient()
    raw_replies = client.get_campaign_replies(campaign.smartlead_id)

    # Remove existing clusters for this campaign
    existing = session.exec(
        select(ReplyCluster).where(ReplyCluster.campaign_id == campaign_id)
    ).all()
    for c in existing:
        session.delete(c)
    session.flush()

    new_clusters = cluster_replies(raw_replies, campaign_id)

    for cluster in new_clusters:
        session.add(cluster)

    session.commit()
    return {"clusters_updated": len(new_clusters)}
