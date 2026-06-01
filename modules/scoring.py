import re
from typing import Dict, List


CTA_PATTERNS = [
    r"book now",
    r"schedule",
    r"request a quote",
    r"get a quote",
    r"free estimate",
    r"apply now",
    r"contact us",
    r"call now",
    r"start now",
    r"learn more",
]

TRACKING_PATTERNS = [
    "gtag(",
    "googletagmanager",
    "gtm.js",
    "google-analytics",
    "facebook pixel",
    "fbq(",
    "linkedin insight",
    "meta pixel",
]


def _safe_str(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_num(value, default=0.0) -> float:
    try:
        if value is None or str(value).strip() == "":
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _text_blob(row: Dict) -> str:
    parts = [
        _safe_str(row.get("title")),
        _safe_str(row.get("meta_description")),
        _safe_str(row.get("h1")),
        _safe_str(row.get("website_notes")),
        _safe_str(row.get("offer_angle")),
        _safe_str(row.get("website_status")),
    ]
    return " | ".join([p for p in parts if p]).lower()


def _website_strength(row: Dict) -> int:
    score = 0
    website = _safe_str(row.get("website"))
    final_url = _safe_str(row.get("final_url"))
    title = _safe_str(row.get("title"))
    h1 = _safe_str(row.get("h1"))
    meta = _safe_str(row.get("meta_description"))
    bad_site = int(_safe_num(row.get("bad_website_score"), 0))
    notes = _safe_str(row.get("website_notes")).lower()

    if website or final_url:
        score += 8
    if title:
        score += 4
    if h1:
        score += 4
    if meta:
        score += 3
    score -= min(8, max(0, bad_site // 10))
    if "missing" in notes or "broken" in notes or "weak" in notes:
        score -= 4

    return max(0, min(25, score))


def _review_strength(row: Dict) -> int:
    rating = _safe_num(row.get("rating"), 0)
    count = _safe_num(row.get("ratings_total"), 0)
    score = 0

    if rating >= 4.5:
        score += 8
    elif rating >= 4.0:
        score += 6
    elif rating >= 3.5:
        score += 4
    elif rating > 0:
        score += 2

    if count >= 200:
        score += 12
    elif count >= 100:
        score += 10
    elif count >= 50:
        score += 7
    elif count >= 20:
        score += 5
    elif count >= 5:
        score += 3

    return max(0, min(20, score))


def _contactability_score(row: Dict) -> int:
    score = 0
    if _safe_str(row.get("primary_email")):
        score += 8
    elif _safe_str(row.get("emails_found")):
        score += 6
    if _safe_str(row.get("primary_phone")) or _safe_str(row.get("phone")):
        score += 6
    if _safe_str(row.get("facebook_link")):
        score += 2
    if _safe_str(row.get("instagram_link")):
        score += 2
    if _safe_str(row.get("linkedin_link")):
        score += 2
    return max(0, min(20, score))


def _cta_strength_score(row: Dict) -> int:
    blob = _text_blob(row)
    if not blob:
        return 0
    matches = sum(1 for pattern in CTA_PATTERNS if re.search(pattern, blob, re.IGNORECASE))
    if matches >= 4:
        return 15
    if matches == 3:
        return 12
    if matches == 2:
        return 8
    if matches == 1:
        return 4
    return 0


def _tracking_detected(row: Dict) -> bool:
    blob = _text_blob(row)
    return any(p in blob for p in TRACKING_PATTERNS)


def _ad_presence(row: Dict) -> Dict:
    website = _safe_str(row.get("website")) or _safe_str(row.get("final_url"))
    tracking = _tracking_detected(row)
    cta = _cta_strength_score(row)

    if website and tracking and cta >= 8:
        return {
            "ad_presence_status": "Likely",
            "ad_presence_reason": "Tracking cues and strong lead-capture language detected.",
            "landing_page_detected": "yes",
            "tracking_detected": "yes",
        }

    if website and (tracking or cta >= 4):
        return {
            "ad_presence_status": "Unknown",
            "ad_presence_reason": "Some marketing cues detected, but not enough to confirm active ads.",
            "landing_page_detected": "unknown",
            "tracking_detected": "yes" if tracking else "unknown",
        }

    return {
        "ad_presence_status": "Not detected",
        "ad_presence_reason": "No meaningful ad or landing-page cues detected from current public data.",
        "landing_page_detected": "no" if not website else "unknown",
        "tracking_detected": "no" if not tracking else "yes",
    }


def _digital_maturity_score(row: Dict) -> int:
    score = 0
    website_strength = _website_strength(row)
    contactability = _contactability_score(row)

    if website_strength >= 18:
        score += 10
    elif website_strength >= 10:
        score += 7
    elif website_strength > 0:
        score += 4

    if contactability >= 14:
        score += 6
    elif contactability >= 8:
        score += 4
    elif contactability > 0:
        score += 2

    ad = _ad_presence(row)
    if ad["ad_presence_status"] == "Likely":
        score += 4
    elif ad["ad_presence_status"] == "Unknown":
        score += 2

    return max(0, min(20, score))


def _needs_leads_score(row: Dict) -> Dict:
    website_strength = _website_strength(row)
    review_strength = _review_strength(row)
    contactability = _contactability_score(row)
    cta_strength = _cta_strength_score(row)
    digital_maturity = _digital_maturity_score(row)

    need = 100
    need -= int(website_strength * 1.2)
    need -= int(review_strength * 1.0)
    need -= int(cta_strength * 1.0)
    need -= int(digital_maturity * 1.0)
    need += int(contactability * 0.8)
    need = max(0, min(100, need))

    reasons = []
    if website_strength <= 8:
        reasons.append("weak website presence")
    if review_strength <= 6:
        reasons.append("light review footprint")
    if cta_strength <= 4:
        reasons.append("weak lead capture")
    if contactability >= 8:
        reasons.append("easy to contact")
    if not reasons:
        reasons.append("balanced opportunity profile")

    if need >= 75:
        tier = "Hot"
    elif need >= 50:
        tier = "Warm"
    else:
        tier = "Cold"

    return {
        "needs_leads_score": need,
        "needs_leads_tier": tier,
        "needs_leads_reason": ", ".join(reasons),
        "website_strength_score": website_strength,
        "review_strength_score": review_strength,
        "contactability_score": contactability,
        "cta_strength_score": cta_strength,
        "digital_maturity_score": digital_maturity,
    }


def _intent_overlay(row: Dict) -> Dict:
    topic = _safe_str(row.get("search_keyword")) or _safe_str(row.get("business_type")) or "general demand"
    topic_lower = topic.lower()

    strength = "medium"
    if any(k in topic_lower for k in ["loan", "mortgage", "med spa", "roof", "dent", "plumb", "clean"]):
        strength = "high"

    return {
        "intent_topic": topic,
        "intent_signal_strength": strength,
        "intent_source_type": "category heuristic",
        "intent_summary": f"Business appears tied to the local demand topic: {topic}.",
    }


def _pitch(row: Dict) -> Dict:
    tier = _safe_str(row.get("needs_leads_tier"))
    topic = _safe_str(row.get("intent_topic")) or _safe_str(row.get("search_keyword")) or "local demand"
    business_name = _safe_str(row.get("name")) or "This business"
    reason = _safe_str(row.get("needs_leads_reason"))

    if "loan" in topic.lower() or "mortgage" in topic.lower():
        angle = "Loan inquiry growth"
        offer = "We can help you generate more qualified loan inquiries from local search and paid demand."
        cta = "Open to a quick conversation about a local lead flow for loan demand?"
    elif "roof" in topic.lower():
        angle = "Home service demand capture"
        offer = "We can help you turn nearby roofing demand into booked estimates and inbound calls."
        cta = "Want a quick breakdown of how we’d generate more estimate requests in your market?"
    else:
        angle = "Local lead generation"
        offer = "We can help you turn local demand into more inbound leads, calls, and booked opportunities."
        cta = "Would it be worth a quick call to show what a lead-generation plan could look like?"

    opening = f"{business_name} looks like a strong local business, but there may be room to improve how demand gets captured."
    pitch_reason = f"Reason flagged: {reason}."

    if tier == "Hot":
        opening = f"{business_name} looks like a high-opportunity lead for immediate marketing outreach."
    elif tier == "Warm":
        opening = f"{business_name} looks like a viable marketing prospect with visible room to improve lead flow."

    return {
        "pitch_angle": angle,
        "pitch_opening_line": opening,
        "pitch_offer": offer,
        "pitch_reason": pitch_reason,
        "pitch_cta": cta,
    }


def score_rows(rows: List[Dict]) -> List[Dict]:
    scored = []

    for row in rows:
        item = dict(row)

        base_score = 0
        if _safe_str(item.get("website")):
            base_score += 20
        if _safe_str(item.get("primary_email")) or _safe_str(item.get("emails_found")):
            base_score += 20
        if _safe_str(item.get("primary_phone")) or _safe_str(item.get("phone")):
            base_score += 15

        rating = _safe_num(item.get("rating"), 0)
        ratings_total = _safe_num(item.get("ratings_total"), 0)

        if rating >= 4.5:
            base_score += 15
        elif rating >= 4.0:
            base_score += 10
        elif rating > 0:
            base_score += 5

        if ratings_total >= 50:
            base_score += 15
        elif ratings_total >= 10:
            base_score += 10
        elif ratings_total > 0:
            base_score += 5

        lead_score = max(0, min(100, int(base_score)))
        if lead_score >= 80:
            lead_tier = "A"
        elif lead_score >= 60:
            lead_tier = "B"
        else:
            lead_tier = "C"

        item["lead_score"] = lead_score
        item["lead_tier"] = lead_tier

        item.update(_needs_leads_score(item))
        item.update(_ad_presence(item))
        item.update(_intent_overlay(item))
        item.update(_pitch(item))

        scored.append(item)

    scored = sorted(
        scored,
        key=lambda r: (
            int(_safe_num(r.get("needs_leads_score"), 0)),
            int(_safe_num(r.get("lead_score"), 0)),
        ),
        reverse=True,
    )

    return scored
