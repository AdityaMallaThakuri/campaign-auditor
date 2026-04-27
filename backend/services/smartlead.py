import os
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

import httpx
from fastapi import HTTPException
from sqlmodel import Session, select

from models.tables import Campaign, SequenceStep

SMARTLEAD_BASE = "https://server.smartlead.ai/api/v1"


def _api_key() -> str:
    key = os.getenv("SMARTLEAD_API_KEY", "") or os.getenv("smartlead_api_key", "")
    if not key:
        raise HTTPException(status_code=503, detail="SMARTLEAD_API_KEY not configured")
    return key


def _get(path: str, params: dict | None = None) -> Any:
    key = _api_key()
    merged = {"api_key": key, **(params or {})}
    try:
        resp = httpx.get(f"{SMARTLEAD_BASE}{path}", params=merged, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text[:500])
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Smartlead unreachable: {e}")


class SmartleadClient:
    # ------------------------------------------------------------------ #
    # Raw API methods                                                      #
    # ------------------------------------------------------------------ #

    def get_campaigns(self) -> list[dict]:
        """List all campaigns (fast — single call, no stats)."""
        data = _get("/campaigns")
        return data if isinstance(data, list) else data.get("data", [])

    def get_campaign_analytics(self, smartlead_id: str) -> dict:
        """
        GET /campaigns/{id}/analytics
        Returns open/reply/bounce counts we use to compute rates.
        """
        data = _get(f"/campaigns/{smartlead_id}/analytics")
        sent = int(data.get("unique_sent_count") or data.get("sent_count") or 0)
        opens = int(data.get("unique_open_count") or data.get("open_count") or 0)
        replies = int(data.get("reply_count") or 0)
        bounces = int(data.get("bounce_count") or 0)
        total = int(data.get("total_count") or 0)

        return {
            "open_rate": round(opens / sent, 4) if sent > 0 else 0.0,
            "reply_rate": round(replies / sent, 4) if sent > 0 else 0.0,
            "bounce_rate": round(bounces / sent, 4) if sent > 0 else 0.0,
            "total_sent": sent,
            "total_leads": total,
        }

    # kept as alias so audit route calling the old name still works
    def get_campaign_stats(self, smartlead_id: str) -> dict:
        return self.get_campaign_analytics(smartlead_id)

    def get_campaign_sequences(self, smartlead_id: str) -> list[dict]:
        """GET /campaigns/{id}/sequences — returns steps with subject + email_body."""
        data = _get(f"/campaigns/{smartlead_id}/sequences")
        return data if isinstance(data, list) else data.get("data", [])

    def get_campaign_replies(self, smartlead_id: str) -> list[dict]:
        """
        GET /campaigns/{id}/statistics — paginated per-lead stats.
        Returns only rows where reply_time is not null.
        """
        replies: list[dict] = []
        offset = 0
        limit = 100
        while True:
            data = _get(f"/campaigns/{smartlead_id}/statistics", {"offset": offset, "limit": limit})
            page: list[dict] = data.get("data", []) if isinstance(data, dict) else data
            if not page:
                break
            for row in page:
                if row.get("reply_time"):
                    replies.append({
                        "lead_email": row.get("lead_email", ""),
                        "lead_category": row.get("lead_category"),   # Smartlead's own categorization
                        "sequence_number": row.get("sequence_number"),
                        "reply_time": row.get("reply_time"),
                    })
            total = int(data.get("total_stats", 0) or 0) if isinstance(data, dict) else 0
            offset += limit
            if offset >= total or len(page) < limit:
                break
        return replies

    def get_campaign_step_stats(self, smartlead_id: str) -> dict[int, dict]:
        """
        Build per-step open/reply rates from /statistics (paginated).
        Returns {step_number: {open_rate, reply_rate, sent}}.
        """
        step_sent: dict[int, int] = defaultdict(int)
        step_opens: dict[int, int] = defaultdict(int)
        step_replies: dict[int, int] = defaultdict(int)

        offset = 0
        limit = 100
        while True:
            data = _get(f"/campaigns/{smartlead_id}/statistics", {"offset": offset, "limit": limit})
            page: list[dict] = data.get("data", []) if isinstance(data, dict) else []
            if not page:
                break
            for row in page:
                seq = int(row.get("sequence_number") or 0)
                if seq == 0:
                    continue
                step_sent[seq] += 1
                if row.get("open_time") or row.get("open_count", 0):
                    step_opens[seq] += 1
                if row.get("reply_time"):
                    step_replies[seq] += 1

            total = int(data.get("total_stats", 0) or 0) if isinstance(data, dict) else 0
            offset += limit
            if offset >= total or len(page) < limit:
                break

        result: dict[int, dict] = {}
        for step in step_sent:
            sent = step_sent[step]
            result[step] = {
                "open_rate": round(step_opens[step] / sent, 4) if sent else 0.0,
                "reply_rate": round(step_replies[step] / sent, 4) if sent else 0.0,
                "sent": sent,
            }
        return result

    # ------------------------------------------------------------------ #
    # Sync helpers                                                         #
    # ------------------------------------------------------------------ #

    def sync_campaigns(self, session: Session, force: bool = False) -> int:
        """
        Fast bulk sync — saves all campaigns from Smartlead list endpoint.
        Does NOT fetch per-campaign sequences or stats (too slow for 400+ campaigns).
        Sequences are fetched lazily via sync_campaign_detail().
        Pass force=True to bypass the TTL cache and always re-fetch.
        """
        from routes.config import get_thresholds
        ttl = get_thresholds().get("cache_ttl_minutes", 30)
        cutoff = datetime.utcnow() - timedelta(minutes=ttl)

        raw = self.get_campaigns()
        count = 0

        for item in raw:
            sl_id = str(item.get("id", ""))
            if not sl_id:
                continue

            existing = session.exec(
                select(Campaign).where(Campaign.smartlead_id == sl_id)
            ).first()

            if not force and existing and existing.fetched_at and existing.fetched_at > cutoff:
                continue  # still fresh — skip

            name = item.get("name", "Unnamed")
            status = (item.get("status") or "active").lower()

            if existing:
                existing.name = name
                existing.status = status
                existing.fetched_at = datetime.utcnow()
                session.add(existing)
            else:
                campaign = Campaign(
                    smartlead_id=sl_id,
                    name=name,
                    status=status,
                    fetched_at=datetime.utcnow(),
                )
                session.add(campaign)

            count += 1

        session.commit()
        return count

    def sync_campaign_detail(self, session: Session, campaign: Campaign) -> None:
        """
        Fetch sequences + per-step stats for a single campaign and upsert
        into sequence_steps. Called from audit/run per campaign.
        """
        try:
            sequences = self.get_campaign_sequences(campaign.smartlead_id)
        except Exception:
            return

        try:
            step_stats = self.get_campaign_step_stats(campaign.smartlead_id)
        except Exception:
            step_stats = {}

        for seq in sequences:
            step_num = int(seq.get("seq_number", 0))
            if step_num == 0:
                continue

            subject = seq.get("subject", "") or ""
            body = seq.get("email_body", "") or ""
            word_count = len(body.split()) if body else 0

            cta = None
            for phrase in ["schedule", "book", "reply", "let me know", "click", "visit", "call"]:
                if phrase in body.lower():
                    cta = phrase
                    break

            stats = step_stats.get(step_num, {})

            existing = session.exec(
                select(SequenceStep)
                .where(SequenceStep.campaign_id == campaign.id)
                .where(SequenceStep.step_number == step_num)
            ).first()

            if existing:
                existing.subject = subject
                existing.body = body
                existing.word_count = word_count
                existing.cta_detected = cta
                existing.open_rate = stats.get("open_rate", existing.open_rate)
                existing.reply_rate = stats.get("reply_rate", existing.reply_rate)
                session.add(existing)
            else:
                session.add(SequenceStep(
                    campaign_id=campaign.id,
                    step_number=step_num,
                    subject=subject,
                    body=body,
                    word_count=word_count,
                    cta_detected=cta,
                    open_rate=stats.get("open_rate", 0.0),
                    reply_rate=stats.get("reply_rate", 0.0),
                ))
