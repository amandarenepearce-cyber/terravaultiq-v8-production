from __future__ import annotations

from typing import Any


def score_audience(estimated_audience_size: int, confidence: str, density_pattern: str, peak_activity_window: str) -> tuple[int, str]:
    score = 40
    if estimated_audience_size < 100:
        score += 0
    elif estimated_audience_size < 1000:
        score += 10
    elif estimated_audience_size < 10000:
        score += 20
    else:
        score += 30

    score += {"low": 5, "medium": 10, "high": 15}.get(confidence, 10)

    has_pattern = bool((density_pattern or "").strip())
    has_window = bool((peak_activity_window or "").strip())
    if has_pattern and has_window:
        score += 15
    elif has_pattern or has_window:
        score += 10
    else:
        score += 5

    score = min(score, 100)
    if score < 50:
        label = "weak"
    elif score < 75:
        label = "fair"
    else:
        label = "strong"
    return score, label


def audience_warning(estimated_audience_size: int) -> dict[str, Any]:
    if estimated_audience_size < 100:
        return {
            "status": "warning",
            "message": "Audience is below the recommended threshold of 100. Consider expanding radius or widening the date range.",
            "suggestions": ["Increase radius", "Expand date range"],
        }
    return {"status": "ok", "message": "Audience meets the recommended threshold.", "suggestions": []}


def next_best_actions(audience: dict[str, Any]) -> list[str]:
    actions: list[str] = []
    estimate = int(audience.get("estimated_audience_size", 0) or 0)
    confidence = audience.get("confidence", "medium")

    if estimate < 100:
        actions.append("Widen radius by 5 miles or expand the date range.")
    if confidence == "low":
        actions.append("Refine the location input to improve confidence.")
    if estimate >= 1000 and confidence in {"medium", "high"}:
        actions.append("Push this audience into LeadGen next.")
    if not audience.get("campaign_name"):
        actions.append("Add a campaign name so this audience can be activated and reported cleanly.")
    if not actions:
        actions.append("Export this audience to Reports and create a reusable template.")
    return actions[:3]
