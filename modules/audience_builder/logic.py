from __future__ import annotations

from datetime import date

from core.recommendations import audience_warning, next_best_actions, score_audience
from core.schema import Audience
from utils.dates import utc_now_iso


def modeled_estimate(radius_value: int, start_date: date, end_date: date, confidence: str) -> int:
    duration_days = max((end_date - start_date).days + 1, 1)
    base = radius_value * duration_days * 55
    multiplier = {"low": 0.8, "medium": 1.0, "high": 1.2}.get(confidence, 1.0)
    return int(round(base * multiplier))


def build_audience(payload: dict) -> dict:
    estimate = modeled_estimate(payload["radius_value"], payload["start_date"], payload["end_date"], payload["confidence"])
    score, label = score_audience(estimate, payload["confidence"], payload["density_pattern"], payload["peak_activity_window"])
    warning = audience_warning(estimate)
    audience = Audience(
        audience_name=payload["audience_name"],
        project_id=payload["project_id"],
        source_module="audience_builder",
        location_input=payload["location_input"],
        normalized_location=payload["location_input"].strip(),
        radius_value=payload["radius_value"],
        start_date=payload["start_date"].isoformat(),
        end_date=payload["end_date"].isoformat(),
        customer_mode=payload["customer_mode"],
        market_region=payload["market_region"],
        campaign_name=payload["campaign_name"],
        channel=payload["channel"],
        notes=payload["notes"],
        estimated_audience_size=estimate,
        estimate_type="modeled",
        confidence=payload["confidence"],
        location_type=payload["location_type"],
        density_pattern=payload["density_pattern"],
        peak_activity_window=payload["peak_activity_window"],
        score=score,
        score_label=label,
        warning_status=warning["status"],
        recommendation_summary=" | ".join(next_best_actions({"estimated_audience_size": estimate, **payload})),
        created_by=payload["created_by"],
        created_at=utc_now_iso(),
        updated_at=utc_now_iso(),
        context_mode="super_tool",
    )
    result = audience.__dict__
    result["warning_message"] = warning["message"]
    result["warning_suggestions"] = warning["suggestions"]
    result["next_best_actions"] = next_best_actions(result)
    return result
