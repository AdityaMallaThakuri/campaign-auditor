import json
import os
from typing import Optional

from fastapi import HTTPException

SYSTEM_PROMPT = (
    "You are an expert cold email strategist. Analyze objectively. "
    "Be specific — reference actual numbers from the data. Never give generic advice."
)


def _client():
    try:
        import anthropic
    except ImportError:
        raise HTTPException(status_code=503, detail="anthropic package not installed")

    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY not configured — AI features unavailable",
        )
    return anthropic.Anthropic(api_key=key)


def diagnose_campaign(campaign, audit, clusters: list) -> dict:
    client = _client()

    cluster_summary = [
        {"category": c.category, "count": c.count, "percentage": c.percentage, "themes": c.themes}
        for c in clusters
    ]

    payload = {
        "campaign_name": campaign.name,
        "status": campaign.status,
        "total_leads": campaign.total_leads,
        "open_rate": audit.open_rate if audit else None,
        "reply_rate": audit.reply_rate if audit else None,
        "bounce_rate": audit.bounce_rate if audit else None,
        "health_score": audit.health_score if audit else None,
        "root_cause": audit.root_cause if audit else None,
        "step_dropoff": audit.step_dropoff if audit else None,
        "reply_clusters": cluster_summary,
    }

    user_msg = (
        f"Diagnose this cold email campaign:\n\n{json.dumps(payload, indent=2)}\n\n"
        "Return ONLY a JSON object with keys: diagnosis (string), root_cause (string), "
        "confidence (high|medium|low), evidence (array of strings)."
    )

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )

    text = response.content[0].text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)


def rewrite_step(step, campaign, instruction: Optional[str] = None) -> dict:
    client = _client()

    payload = {
        "campaign_name": campaign.name,
        "step_number": step.step_number,
        "subject": step.subject,
        "body": step.body,
        "word_count": step.word_count,
        "cta_detected": step.cta_detected,
        "open_rate": step.open_rate,
        "reply_rate": step.reply_rate,
    }
    if instruction:
        payload["instruction"] = instruction

    user_msg = (
        f"Rewrite this cold email sequence step:\n\n{json.dumps(payload, indent=2)}\n\n"
        "Return ONLY a JSON object with keys: rewrite (string), "
        "subject_alternatives (array of 3 strings), rationale (string)."
    )

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)
