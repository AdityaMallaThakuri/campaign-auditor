from typing import Optional


def calculate_health_score(open_rate: float, reply_rate: float, bounce_rate: float) -> int:
    # Open component: 40 pts — full at >35%, zero at <10%
    if open_rate >= 0.35:
        open_pts = 40.0
    elif open_rate <= 0.10:
        open_pts = 0.0
    else:
        open_pts = 40.0 * (open_rate - 0.10) / (0.35 - 0.10)

    # Reply component: 45 pts — full at >5%, zero at <0.5%
    if reply_rate >= 0.05:
        reply_pts = 45.0
    elif reply_rate <= 0.005:
        reply_pts = 0.0
    else:
        reply_pts = 45.0 * (reply_rate - 0.005) / (0.05 - 0.005)

    # Bounce component: 15 pts — full at <2%, zero at >8%
    if bounce_rate <= 0.02:
        bounce_pts = 15.0
    elif bounce_rate >= 0.08:
        bounce_pts = 0.0
    else:
        bounce_pts = 15.0 * (0.08 - bounce_rate) / (0.08 - 0.02)

    return min(100, max(0, round(open_pts + reply_pts + bounce_pts)))


def diagnose_root_cause(
    open_rate: float,
    reply_rate: float,
    bounce_rate: float,
    step_dropoff: Optional[dict],
    reply_clusters: list,
) -> tuple[str, str]:
    if bounce_rate > 0.05:
        return (
            "deliverability",
            f"Bounce rate {bounce_rate:.1%} exceeds 5% threshold — emails are not reaching inboxes. "
            "Check sending domain authentication (SPF, DKIM, DMARC), warm-up status, and list quality.",
        )

    if open_rate < 0.20:
        return (
            "subject",
            f"Open rate {open_rate:.1%} is below 20% — subject lines are failing to generate opens. "
            "Test shorter subjects, personalisation tokens, and question-format subjects.",
        )

    if reply_rate < 0.03 and open_rate >= 0.20:
        return (
            "copy",
            f"Open rate {open_rate:.1%} is acceptable but reply rate {reply_rate:.1%} is below 3%. "
            "The body copy is not compelling enough to drive replies. "
            "Review the value proposition, CTA clarity, and email length.",
        )

    # Check for not_relevant targeting signal
    total_cluster_count = sum(getattr(c, "count", 0) for c in reply_clusters)
    if total_cluster_count > 0:
        not_relevant = next(
            (c for c in reply_clusters if getattr(c, "category", "") == "not_relevant"), None
        )
        if not_relevant and (not_relevant.count / total_cluster_count) > 0.40:
            return (
                "targeting",
                f"{not_relevant.percentage:.1f}% of replies indicate the message is not relevant to recipients. "
                "Review your lead list segmentation and ICP definition.",
            )

    return (
        "copy",
        f"Metrics are borderline — open rate {open_rate:.1%}, reply rate {reply_rate:.1%}. "
        "Focus on improving copy clarity and CTA strength.",
    )


def detect_dropoff(sequence_steps: list) -> dict:
    result: dict = {"dropoff_at_step": None, "steps": []}

    for step in sequence_steps:
        result["steps"].append({
            "step_number": step.step_number,
            "open_rate": step.open_rate,
            "reply_rate": step.reply_rate,
        })

    prev_reply_rate: Optional[float] = None
    for step in sequence_steps:
        if prev_reply_rate is not None and prev_reply_rate > 0:
            drop_pct = (prev_reply_rate - step.reply_rate) / prev_reply_rate
            if drop_pct > 0.50:
                result["dropoff_at_step"] = step.step_number
                break
        if step.reply_rate > 0:
            prev_reply_rate = step.reply_rate

    return result


def detect_decay(audit_snapshots: list) -> bool:
    if len(audit_snapshots) < 2:
        return False
    from datetime import timedelta

    latest = audit_snapshots[-1]
    cutoff = latest.audited_at - timedelta(days=7)
    week_ago = next(
        (s for s in reversed(audit_snapshots[:-1]) if s.audited_at <= cutoff), None
    )
    if week_ago is None:
        return False
    return (week_ago.health_score - latest.health_score) > 15
