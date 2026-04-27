import os
from datetime import datetime, timedelta
from typing import Any

import httpx
from fastapi import HTTPException
from sqlmodel import Session, select

from models.tables import Campaign, SequenceStep

SMARTLEAD_BASE = "https://server.smartlead.ai/api/v1"


def _api_key() -> str:
    key = os.getenv("SMARTLEAD_API_KEY", "")
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
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Smartlead unreachable: {e}")


class SmartleadClient:
    def get_campaigns(self) -> list[dict]:
        data = _get("/campaigns")
        if isinstance(data, list):
            return data
        return data.get("data", data.get("campaigns", []))

    def get_campaign_stats(self, smartlead_id: str) -> dict:
        data = _get(f"/campaigns/{smartlead_id}/campaign-stats")
        # Normalise keys to open_rate / reply_rate / bounce_rate as fractions
        stats = data if isinstance(data, dict) else {}
        def pct(key: str, alt: str = "") -> float:
            v = stats.get(key, stats.get(alt, 0)) or 0
            return float(v) / 100.0 if float(v) > 1 else float(v)

        return {
            "open_rate": pct("open_rate", "open_percentage"),
            "reply_rate": pct("reply_rate", "reply_percentage"),
            "bounce_rate": pct("bounce_rate", "bounce_percentage"),
            "total_sent": stats.get("total_sent", stats.get("sent_count", 0)),
        }

    def get_campaign_sequences(self, smartlead_id: str) -> list[dict]:
        data = _get(f"/campaigns/{smartlead_id}/sequences")
        if isinstance(data, list):
            return data
        return data.get("data", data.get("sequences", []))

    def get_campaign_replies(self, smartlead_id: str) -> list[dict]:
        all_replies: list[dict] = []
        offset = 0
        limit = 100
        while True:
            data = _get(
                f"/campaigns/{smartlead_id}/leads-with-reply",
                {"offset": offset, "limit": limit},
            )
            page = data if isinstance(data, list) else data.get("data", [])
            if not page:
                break
            all_replies.extend(page)
            if len(page) < limit:
                break
            offset += limit
        return all_replies

    def sync_campaigns(self, session: Session) -> int:
        from routes.config import get_thresholds
        ttl = get_thresholds().get("cache_ttl_minutes", 30)
        cutoff = datetime.utcnow() - timedelta(minutes=ttl)

        raw = self.get_campaigns()
        count = 0

        for item in raw:
            sl_id = str(item.get("id", item.get("smartlead_id", "")))
            if not sl_id:
                continue

            existing = session.exec(
                select(Campaign).where(Campaign.smartlead_id == sl_id)
            ).first()

            if existing and existing.fetched_at and existing.fetched_at > cutoff:
                continue  # still fresh

            name = item.get("name", item.get("campaign_name", "Unnamed"))
            status = item.get("status", "active").lower()
            total_leads = item.get("total_lead_count", item.get("total_leads", 0)) or 0

            if existing:
                existing.name = name
                existing.status = status
                existing.total_leads = total_leads
                existing.fetched_at = datetime.utcnow()
                session.add(existing)
                campaign = existing
            else:
                campaign = Campaign(
                    smartlead_id=sl_id,
                    name=name,
                    status=status,
                    total_leads=total_leads,
                    fetched_at=datetime.utcnow(),
                )
                session.add(campaign)
                session.flush()  # get campaign.id

            # Sync sequences
            try:
                sequences = self.get_campaign_sequences(sl_id)
                self._upsert_steps(session, campaign.id, sequences)
            except Exception:
                pass  # sequences failing shouldn't abort the sync

            count += 1

        session.commit()
        return count

    def _upsert_steps(self, session: Session, campaign_id: int, sequences: list[dict]):
        for i, seq in enumerate(sequences, start=1):
            existing_step = session.exec(
                select(SequenceStep)
                .where(SequenceStep.campaign_id == campaign_id)
                .where(SequenceStep.step_number == i)
            ).first()

            subject = seq.get("subject", "")
            body = seq.get("body", seq.get("email_body", ""))
            word_count = len(body.split()) if body else 0

            # Naive CTA detection
            cta = None
            for phrase in ["schedule", "book", "reply", "let me know", "click", "visit", "call"]:
                if phrase in body.lower():
                    cta = phrase
                    break

            if existing_step:
                existing_step.subject = subject
                existing_step.body = body
                existing_step.word_count = word_count
                existing_step.cta_detected = cta
                session.add(existing_step)
            else:
                session.add(SequenceStep(
                    campaign_id=campaign_id,
                    step_number=i,
                    subject=subject,
                    body=body,
                    word_count=word_count,
                    cta_detected=cta,
                ))
