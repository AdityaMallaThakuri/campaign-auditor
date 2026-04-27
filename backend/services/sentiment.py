from collections import Counter
from datetime import datetime
from models.tables import ReplyCluster

# Map Smartlead's lead_category values → our canonical categories
SMARTLEAD_CATEGORY_MAP: dict[str, str] = {
    "interested": "interested",
    "booked": "interested",
    "meeting request": "interested",
    "information request": "interested",
    "positive response but no reply": "interested",
    "not interested": "not_relevant",
    "do not contact": "not_relevant",
    "out of office": "timing",
    "wrong person": "wrong_person",
    "competitor": "competitor",
    "budget": "price_objection",
    "pricing": "price_objection",
}

# Fallback keyword matching (used when lead_category is null)
KEYWORD_MAP: dict[str, list[str]] = {
    "interested": ["interested", "let's chat", "tell me more", "book", "call", "demo", "yes"],
    "price_objection": ["budget", "expensive", "cost", "price", "afford", "pricing"],
    "timing": ["not now", "later", "next quarter", "busy", "bad time", "reach out"],
    "wrong_person": ["not the right", "wrong person", "someone else", "not my area", "forward"],
    "not_relevant": ["not relevant", "not interested", "remove", "unsubscribe", "don't contact"],
    "competitor": ["already use", "using", "we have", "partner"],
}


def _classify_by_smartlead_category(category: str | None) -> str | None:
    if not category:
        return None
    return SMARTLEAD_CATEGORY_MAP.get(category.lower().strip())


def _classify_by_keywords(text: str) -> str:
    lower = text.lower()
    for category, keywords in KEYWORD_MAP.items():
        if any(kw in lower for kw in keywords):
            return category
    return "other"


def cluster_replies(reply_dicts: list[dict], campaign_id: int) -> list[ReplyCluster]:
    """
    Cluster replies using Smartlead's lead_category as the primary signal.
    Falls back to keyword matching on reply text when lead_category is absent.
    reply_dicts: list of dicts with keys: lead_category, lead_email, sequence_number
    """
    buckets: dict[str, list[dict]] = {}

    for reply in reply_dicts:
        if not reply:
            continue
        # Primary: use Smartlead's own categorisation
        cat = _classify_by_smartlead_category(reply.get("lead_category"))
        # Fallback: keyword matching (text key may be absent — treated as "other")
        if cat is None:
            cat = _classify_by_keywords(reply.get("text", ""))
        buckets.setdefault(cat, []).append(reply)

    total = sum(len(v) for v in buckets.values())
    clusters: list[ReplyCluster] = []

    for category, replies in buckets.items():
        count = len(replies)
        percentage = round((count / total) * 100, 1) if total > 0 else 0.0

        # Use Smartlead's raw categories as themes (more informative than word frequency)
        raw_cats = [r.get("lead_category") for r in replies if r.get("lead_category")]
        themes = [cat for cat, _ in Counter(raw_cats).most_common(3)] if raw_cats else [category]

        # sample_replies: show lead emails as proxy (no reply text available from API)
        samples = [r.get("lead_email", "") for r in replies[:5] if r.get("lead_email")]

        clusters.append(
            ReplyCluster(
                campaign_id=campaign_id,
                category=category,
                count=count,
                percentage=percentage,
                sample_replies=samples,
                themes=themes,
                clustered_at=datetime.utcnow(),
            )
        )

    return clusters
