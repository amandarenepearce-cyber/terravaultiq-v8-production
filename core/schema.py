from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

from utils.dates import utc_now_iso


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


@dataclass
class Project:
    project_id: str = field(default_factory=lambda: make_id("proj"))
    project_name: str = ""
    account_name: str = ""
    created_by: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    status: str = "active"
    notes: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class Audience:
    audience_id: str = field(default_factory=lambda: make_id("aud"))
    audience_name: str = ""
    project_id: str = ""
    source_module: str = "audience_builder"
    location_input: str = ""
    normalized_location: str = ""
    latitude: str = ""
    longitude: str = ""
    radius_value: int = 5
    radius_unit: str = "miles"
    start_date: str = ""
    end_date: str = ""
    customer_mode: str = "ignore"
    market_region: str = ""
    campaign_name: str = ""
    channel: str = ""
    notes: str = ""
    estimated_audience_size: int = 0
    estimate_type: str = "modeled"
    confidence: str = "medium"
    location_type: str = "unknown"
    density_pattern: str = "mixed"
    peak_activity_window: str = "all week"
    score: int = 0
    score_label: str = "weak"
    warning_status: str = "ok"
    recommendation_summary: str = ""
    created_by: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    context_mode: str = "super_tool"


@dataclass
class LeadOpportunity:
    lead_id: str = field(default_factory=lambda: make_id("lead"))
    project_id: str = ""
    audience_id: str = ""
    lead_type: str = "geo_segment"
    segment_name: str = ""
    opportunity_score: int = 0
    reason_summary: str = ""
    next_best_action: str = ""
    export_status: str = "not_exported"
    created_at: str = field(default_factory=utc_now_iso)


@dataclass
class ExportRecord:
    export_id: str = field(default_factory=lambda: make_id("exp"))
    project_id: str = ""
    audience_id: str = ""
    module_name: str = "reports"
    export_type: str = "json"
    file_name: str = ""
    generated_by: str = ""
    generated_at: str = field(default_factory=utc_now_iso)
    delivery_status: str = "generated"


@dataclass
class AuditEvent:
    event_id: str = field(default_factory=lambda: make_id("evt"))
    project_id: str = ""
    entity_type: str = ""
    entity_id: str = ""
    event_type: str = ""
    event_summary: str = ""
    actor: str = ""
    timestamp: str = field(default_factory=utc_now_iso)
    module_name: str = ""


def to_dict(instance: Any) -> dict[str, Any]:
    return asdict(instance)
