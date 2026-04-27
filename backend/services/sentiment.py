from collections import Counter
from datetime import datetime
from models.tables import ReplyCluster

KEYWORD_MAP: dict[str, list[str]] = {
    "interested": ["interested", "let's chat", "tell me more", "book", "call", "demo", "yes"],
    "price_objection": ["budget", "expensive", "cost", "price", "afford", "pricing"],
    "timing": ["not now", "later", "next quarter", "busy", "bad time", "reach out"],
    "wrong_person": ["not the right", "wrong person", "someone else", "not my area", "forward"],
    "not_relevant": ["not relevant", "not interested", "remove", "unsubscribe", "don't contact"],
    "competitor": ["already use", "using", "we have", "partner"],
}


def _classify(text: str) -> str:
    lower = text.lower()
    for category, keywords in KEYWORD_MAP.items():
        if any(kw in lower for kw in keywords):
            return category
    return "other"


def _top_phrases(texts: list[str], n: int = 3) -> list[str]:
    words: list[str] = []
    stop = {"the", "a", "an", "is", "it", "we", "i", "to", "and", "for", "in", "of", "on", "at", "be"}
    for text in texts:
        words.extend(w.lower().strip(".,!?") for w in text.split() if w.lower() not in stop and len(w) > 2)
    return [w for w, _ in Counter(words).most_common(n)]


def cluster_replies(reply_texts: list[str], campaign_id: int) -> list[ReplyCluster]:
    buckets: dict[str, list[str]] = {}
    for text in reply_texts:
        if not text or not text.strip():
            continue
        cat = _classify(text)
        buckets.setdefault(cat, []).append(text)

    total = sum(len(v) for v in buckets.values())
    clusters: list[ReplyCluster] = []

    for category, texts in buckets.items():
        count = len(texts)
        percentage = round((count / total) * 100, 1) if total > 0 else 0.0
        sample_replies = texts[:5]
        themes = _top_phrases(texts, n=3)

        clusters.append(
            ReplyCluster(
                campaign_id=campaign_id,
                category=category,
                count=count,
                percentage=percentage,
                sample_replies=sample_replies,
                themes=themes,
                clustered_at=datetime.utcnow(),
            )
        )

    return clusters
