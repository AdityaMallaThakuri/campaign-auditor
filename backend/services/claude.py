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


def _call(client, **kwargs) -> str:
    """Wrap messages.create with clean error conversion for Anthropic API errors."""
    try:
        import anthropic
        response = client.messages.create(**kwargs)
        return response.content[0].text
    except anthropic.AuthenticationError:
        raise HTTPException(status_code=401, detail="Anthropic API key is invalid")
    except anthropic.PermissionDeniedError as e:
        raise HTTPException(status_code=402, detail=f"Anthropic account issue: {e.message}")
    except anthropic.BadRequestError as e:
        msg = str(e)
        if "credit balance" in msg.lower():
            raise HTTPException(status_code=402, detail="Anthropic account has no credits — add credits at console.anthropic.com")
        raise HTTPException(status_code=400, detail=f"Anthropic bad request: {msg[:200]}")
    except anthropic.RateLimitError:
        raise HTTPException(status_code=429, detail="Anthropic rate limit hit — try again in a moment")
    except anthropic.APIConnectionError:
        raise HTTPException(status_code=503, detail="Could not reach Anthropic API — check your internet connection")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Anthropic API error: {str(e)[:200]}")


def _extract_json(text: str) -> dict:
    """Extract the first JSON object from a Claude response, ignoring markdown fences."""
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise HTTPException(
            status_code=500,
            detail=f"Claude returned no JSON object. Response: {text[:300]}",
        )
    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Claude returned malformed JSON: {e}. Raw: {text[start:end][:300]}",
        )


def diagnose_campaign(campaign, audit, clusters: list) -> dict:
    client = _client()

    cluster_summary = [
        {
            "category": c.category,
            "count": c.count,
            "percentage": c.percentage,
            "themes": c.themes,
        }
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
        f"Diagnose this cold email campaign and explain exactly why it is underperforming:\n\n"
        f"{json.dumps(payload, indent=2)}\n\n"
        "Return ONLY a JSON object with these exact keys:\n"
        "  diagnosis   — 2-4 sentence analysis referencing specific numbers\n"
        "  root_cause  — single word: deliverability | subject | copy | targeting\n"
        "  confidence  — high | medium | low\n"
        "  evidence    — array of 3-5 specific observations from the data"
    )

    text = _call(
        _client(),
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    return _extract_json(text)


def rewrite_step(step, campaign, instruction: Optional[str] = None) -> dict:
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
        f"Rewrite this cold email sequence step to improve reply rate:\n\n"
        f"{json.dumps(payload, indent=2)}\n\n"
        "Return ONLY a JSON object with these exact keys:\n"
        "  rewrite              — the full rewritten email body (keep placeholders like {{first_name}})\n"
        "  subject_alternatives — array of exactly 3 subject line options\n"
        "  rationale            — 1-2 sentences explaining the specific changes made and why"
    )

    text = _call(
        _client(),
        model="claude-sonnet-4-5",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    return _extract_json(text)
