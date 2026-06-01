from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from datetime import datetime, timezone
from typing import Any

DISPLAY_SIZES = ["300x250", "320x50", "160x600", "728x90"]


def _clean(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _slug(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return text or "activation-package"


def build_activation_payload(project: dict[str, Any], audience: dict[str, Any], offer: str | None = None) -> dict[str, Any]:
    brand = _clean(project.get("account_name"), _clean(project.get("project_name"), "Midwest Horizons Marketing"))
    audience_name = _clean(audience.get("audience_name"), "local homeowners")
    campaign_name = _clean(audience.get("campaign_name"), audience_name)
    market = _clean(audience.get("market_region"), _clean(audience.get("normalized_location"), _clean(audience.get("location_input"), "local market")))
    channel = _clean(audience.get("channel"), "multi-channel")
    final_offer = _clean(offer, _clean(audience.get("offer"), "Get a better website that turns local homeowners into booked estimates and calls."))
    lead_count = int(audience.get("estimated_audience_size") or 0)

    copy_variants = [
        {
            "variant_id": "A1",
            "platform": "meta",
            "campaign_type": "local-leads",
            "audience_stage": "cold",
            "asset_type": "primary-text",
            "angle": "pain-to-solution",
            "headline": "Is Your Website Costing You Local Customers?",
            "primary_text": f"Homeowners in {market} are searching before they call. If your site looks outdated, loads slowly, or does not make the next step obvious, those leads go somewhere else. Midwest Horizons can help turn your website into a local lead engine.",
            "description": "Get a website plan built for calls, forms, and booked estimates.",
            "cta": "Get Website Plan",
            "size": "",
            "landing_page_hint": "Repeat the lost-leads problem and show a simple website upgrade path.",
            "notes": "Strong cold prospecting angle."
        },
        {
            "variant_id": "A2",
            "platform": "meta",
            "campaign_type": "local-leads",
            "audience_stage": "cold",
            "asset_type": "primary-text",
            "angle": "outcome/desire",
            "headline": "Turn More Local Searches Into Calls",
            "primary_text": f"Your next customer may already be looking in {market}. A clearer, faster, better website can make your business easier to trust and easier to contact.",
            "description": "See what a conversion-focused website could do for your business.",
            "cta": "See Website Options",
            "size": "",
            "landing_page_hint": "Lead with more calls, more form fills, and a cleaner customer journey.",
            "notes": "Softer outcome angle."
        },
        {
            "variant_id": "B1",
            "platform": "google-search",
            "campaign_type": "local-leads",
            "audience_stage": "hot",
            "asset_type": "headline",
            "angle": "proof/differentiation",
            "headline": "Website Design For Local Leads",
            "primary_text": "",
            "description": "Built to convert visitors into calls, quotes, and booked appointments.",
            "cta": "Book Consultation",
            "size": "",
            "landing_page_hint": "Use trust cues, sample layouts, and a direct booking form.",
            "notes": "Search intent variant."
        },
        {
            "variant_id": "B2",
            "platform": "google-search",
            "campaign_type": "local-leads",
            "audience_stage": "hot",
            "asset_type": "headline",
            "angle": "pain-to-solution",
            "headline": "Fix Your Outdated Website",
            "primary_text": "",
            "description": "Make your site faster, clearer, and easier for customers to contact you.",
            "cta": "Request Website Review",
            "size": "",
            "landing_page_hint": "Offer a no-pressure website review and next-step plan.",
            "notes": "Direct pain hook."
        },
        {
            "variant_id": "C1",
            "platform": "email",
            "campaign_type": "prospecting",
            "audience_stage": "cold",
            "asset_type": "outreach",
            "angle": "pain-to-solution",
            "headline": "Quick website idea for your local leads",
            "primary_text": "I was looking at local businesses in your market and noticed a lot of companies are losing calls because their websites do not make the next step obvious. We help businesses turn their websites into cleaner, faster lead-generation tools. Want me to send over a quick idea for yours?",
            "description": "Cold email starter.",
            "cta": "Reply for quick idea",
            "size": "",
            "landing_page_hint": "Match email promise with a quick website review form.",
            "notes": "Use as first touch."
        },
        {
            "variant_id": "D1",
            "platform": "sms",
            "campaign_type": "prospecting",
            "audience_stage": "cold",
            "asset_type": "outreach",
            "angle": "outcome/desire",
            "headline": "Website lead idea",
            "primary_text": "Hi, this is Midwest Horizons. We help local businesses turn more website visits into calls and quote requests. Want a quick website improvement idea?",
            "description": "SMS opener.",
            "cta": "Reply YES",
            "size": "",
            "landing_page_hint": "Use a short mobile-first page with one CTA.",
            "notes": "Use only where compliant and permissioned."
        },
    ]

    display_units = []
    for idx, size in enumerate(DISPLAY_SIZES, start=1):
        display_units.append({
            "variant_id": f"G{idx}",
            "platform": "google-display",
            "campaign_type": "local-leads",
            "audience_stage": "cold",
            "asset_type": "banner",
            "angle": "outcome/desire",
            "headline": "More Local Calls From Your Website",
            "primary_text": "Turn visitors into leads.",
            "description": "Website plans for local businesses.",
            "cta": "Get Plan",
            "size": size,
            "landing_page_hint": "Keep headline identical or very close to the ad promise.",
            "notes": "Short copy required for small placements."
        })

    return {
        "brand": brand,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "campaign": {
            "name": campaign_name,
            "objective": "lead generation",
            "industry": "local service business marketing / website sales",
            "funnel_stage": "cold",
            "offer": final_offer,
            "primary_framework": "pas",
            "support_lens": "local relevance",
            "channel": channel,
            "desired_action": "book a website consultation or request a website review",
        },
        "audiences": [{
            "name": audience_name,
            "market": market,
            "estimated_size": lead_count,
            "score": audience.get("score"),
            "score_label": audience.get("score_label"),
            "pain_or_desire": "wants more local calls, estimates, and trust from website visitors",
            "objection": "not sure a new website will pay for itself",
            "radius": f"{audience.get('radius_value', '')} {audience.get('radius_unit', 'miles')}".strip(),
        }],
        "angles": [
            {"priority": 1, "angle": "pain-to-solution", "message_core": "Your website may be leaking local leads.", "proof_cue": "clearer path to calls and quote requests", "cta": "Get Website Plan", "why": "It connects a visible business problem to an immediate fix."},
            {"priority": 2, "angle": "outcome/desire", "message_core": "Turn more local searches into calls.", "proof_cue": "conversion-focused pages and mobile-first layout", "cta": "See Website Options", "why": "It sells the business outcome, not just design."},
            {"priority": 3, "angle": "proof/differentiation", "message_core": "Built for local lead generation, not just a prettier site.", "proof_cue": "forms, calls, tracking, and offer clarity", "cta": "Book Consultation", "why": "It separates Midwest Horizons from generic web designers."},
        ],
        "assets": {"copy_variants": copy_variants + display_units, "display_units": display_units},
        "landing_page": {
            "headline": "Turn More Local Website Visitors Into Calls And Quotes",
            "subheadline": "Midwest Horizons builds conversion-focused websites for local businesses that need clearer offers, better trust, and easier ways for customers to take action.",
            "proof_bullets": ["Built around calls, forms, and booked estimates", "Mobile-first layouts for local buyers", "Campaign-ready pages for ads and outreach"],
            "primary_cta": "Request My Website Plan",
            "secondary_cta": "Get A Quick Website Review",
            "bridge_note": "The first screen should mirror the winning ad hook so visitors instantly know they landed in the right place."
        },
        "objections": [
            {"objection": "A website is too expensive.", "reframe": "A weak website can quietly cost more in missed calls than the upgrade.", "soft_cta": "See options", "direct_cta": "Get quote"},
            {"objection": "I already have a website.", "reframe": "The question is whether it is producing leads, not whether it exists.", "soft_cta": "Request review", "direct_cta": "Book consultation"},
            {"objection": "I do not have time for a rebuild.", "reframe": "Start with the pages that create the most customer action first.", "soft_cta": "See plan", "direct_cta": "Start project"},
        ],
        "testing": {
            "root_test": "hook_family",
            "branches": [
                {"test": "pain_vs_outcome_vs_proof", "win_metric": "lead rate", "threshold": "20 percent above baseline", "next": "test CTA strength and landing page headline match"},
                {"test": "soft_review_cta_vs_direct_consultation_cta", "win_metric": "qualified conversations", "threshold": "lower cost per qualified lead", "next": "scale winner by audience and market"},
            ]
        },
        "recommended_launch_order": ["meta pain hook prospecting", "google search direct intent", "display retargeting", "email follow-up", "sms follow-up where compliant"],
        "display_sizes": DISPLAY_SIZES,
    }


def _write_csv(rows: list[dict[str, Any]], headers: list[str]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


def files_for_package(payload: dict[str, Any]) -> dict[str, str]:
    campaign = payload["campaign"]
    audience = payload["audiences"][0]
    angles = payload["angles"]
    variants = payload["assets"]["copy_variants"]

    campaign_brief = f"""# Campaign Brief\n\n## Brand\n{payload['brand']}\n\n## Objective\n{campaign['objective']}\n\n## Industry\n{campaign['industry']}\n\n## Audience\n{audience['name']} in {audience['market']}\n\n## Funnel stage\n{campaign['funnel_stage']}\n\n## Offer\n{campaign['offer']}\n\n## Primary framework\n{campaign['primary_framework']}\n\n## Support lens\n{campaign['support_lens']}\n\n## Core pain or desire\n{audience['pain_or_desire']}\n\n## Strongest proof\nConversion-focused website structure built around calls, forms, and booked estimates.\n\n## Main objection\n{audience['objection']}\n\n## Desired action\n{campaign['desired_action']}\n\n## Assumptions\n- Audience is modeled from TerraVaultIQ audience data.\n- Campaign is designed for Midwest Horizons internal website sales outreach.\n- Compliance review is required before SMS or cold outreach at scale.\n"""

    angle_rows = "\n".join([f"| {a['priority']} | {a['angle']} | cold | {a['message_core']} | {a['proof_cue']} | {a['cta']} | {a['why']} |" for a in angles])
    angle_map = "# Angle Map\n\n| priority | angle | audience stage | message core | proof cue | cta | why it should work |\n|---|---|---|---|---|---|---|\n" + angle_rows + "\n"

    ad_headers = ["platform","campaign_type","audience_stage","asset_type","angle","headline","primary_text","description","cta","size","variant_id","landing_page_hint","notes"]
    ad_csv = _write_csv(variants, ad_headers)

    creative_prompts = """# Creative Prompts\n\n## Lost Leads Website Audit\n- angle: pain-to-solution\n- intended platform: meta/display\n- static prompt: A local service business owner looking at a laptop with missed call notifications and a cleaner website mockup beside it. Professional, local, trustworthy, modern.\n- motion prompt: Start with a cluttered outdated website, transition to a clean lead-focused homepage with call and quote buttons.\n- text overlay: Is your website leaking local leads?\n- trust cue: Website plans built for calls and quotes.\n- placement note: Keep text large and high contrast for mobile feeds.\n\n## More Calls From Local Search\n- angle: outcome/desire\n- intended platform: meta/google-display\n- static prompt: Local homeowner searching on phone, business website appears clearly with click-to-call and quote form.\n- motion prompt: Search to website visit to phone call conversion sequence.\n- text overlay: More local searches. More calls.\n- trust cue: Built by Midwest Horizons Marketing.\n- placement note: Use simple visuals, not busy dashboards.\n"""

    display_ads = "# Display Ads\n\n"
    for unit in payload["assets"]["display_units"]:
        display_ads += f"## {unit['size']}\n- primary line: {unit['headline']}\n- backup line: {unit['primary_text']}\n- cta: {unit['cta']}\n- layout intent: simple business-growth message with one clear action\n- visual direction: local business website mockup plus phone/call cue\n- must remain legible: headline and CTA\n- character discipline: keep copy short for small placements\n\n"

    objection_bank = "# Objection Bank\n\n" + "\n".join([f"## {i+1}. {o['objection']}\n- reframe: {o['reframe']}\n- softer CTA: {o['soft_cta']}\n- direct CTA: {o['direct_cta']}\n" for i, o in enumerate(payload["objections"])])

    lp = payload["landing_page"]
    landing_page_sync = f"""# Landing Page Sync\n\n## headline\n{lp['headline']}\n\n## subheadline\n{lp['subheadline']}\n\n## proof bullets\n""" + "\n".join([f"- {b}" for b in lp["proof_bullets"]]) + f"\n\n## primary cta\n{lp['primary_cta']}\n\n## secondary cta\n{lp['secondary_cta']}\n\n## bridge note\n{lp['bridge_note']}\n"

    persona_map = """# Persona Map\n\n| persona | core desire or pain | dominant objection | awareness | sophistication | recommended hook family | recommended CTA |\n|---|---|---|---|---|---|---|\n| busy owner | wants more calls without babysitting marketing | no time for a rebuild | problem-aware | 2 | pain-to-solution | request review |\n| growth owner | wants more booked estimates and better trust | unsure ROI is there | solution-aware | 3 | outcome/desire | get website plan |\n| skeptical owner | has been burned by marketing before | does not trust agencies | product-aware | 4 | proof/differentiation | book consultation |\n"""

    test_rows = [
        {"test_id":"T1","priority":1,"angle":"pain-to-solution","audience_stage":"cold","channel":"meta","creative_type":"static","hypothesis":"Lost-lead messaging will create the highest CTR.","primary_signal":"CTR","secondary_signal":"lead rate","next_action_if_wins":"Build 3 more pain variants.","next_action_if_loses":"Move budget to outcome angle."},
        {"test_id":"T2","priority":2,"angle":"outcome/desire","audience_stage":"cold","channel":"google-display","creative_type":"banner","hypothesis":"More calls promise will work in compact display units.","primary_signal":"CTR","secondary_signal":"CPC","next_action_if_wins":"Expand display placements.","next_action_if_loses":"Use retargeting only."},
        {"test_id":"T3","priority":3,"angle":"proof/differentiation","audience_stage":"warm","channel":"email","creative_type":"outreach","hypothesis":"Website review CTA reduces friction.","primary_signal":"reply rate","secondary_signal":"qualified consults","next_action_if_wins":"Add second follow-up.","next_action_if_loses":"Change offer to free homepage teardown."},
    ]
    test_headers = ["test_id","priority","angle","audience_stage","channel","creative_type","hypothesis","primary_signal","secondary_signal","next_action_if_wins","next_action_if_loses"]
    testing_csv = _write_csv(test_rows, test_headers)

    manifest = {
        "brand": payload["brand"],
        "objective": campaign["objective"],
        "industry": campaign["industry"],
        "audiences": [audience["name"]],
        "frameworks_used": [campaign["primary_framework"], campaign["support_lens"]],
        "output_files": ["campaign-brief.md", "angle-map.md", "ad-copy.csv", "creative-prompts.md", "display-ads.md", "testing-matrix.csv", "persona-map.md", "objection-bank.md", "landing-page-sync.md", "test-tree.json", "ad-studio-input.json", "activation-readme.md", "package-manifest.json"],
        "display_sizes": DISPLAY_SIZES,
        "recommended_launch_order": payload["recommended_launch_order"],
        "generated_at": payload["generated_at"],
    }

    readme = """# Activation Package README\n\nThis package was generated by TerraVaultIQ Activation Studio.\n\nUse campaign-brief.md to understand the strategy, ad-copy.csv for copy upload/planning, display-ads.md for banner production, landing-page-sync.md for the destination page, and testing-matrix.csv for launch sequencing.\n\nBefore sending SMS or cold outreach at scale, review compliance rules and consent requirements.\n"""

    return {
        "campaign-brief.md": campaign_brief,
        "angle-map.md": angle_map,
        "ad-copy.csv": ad_csv,
        "creative-prompts.md": creative_prompts,
        "display-ads.md": display_ads,
        "testing-matrix.csv": testing_csv,
        "persona-map.md": persona_map,
        "objection-bank.md": objection_bank,
        "landing-page-sync.md": landing_page_sync,
        "test-tree.json": json.dumps(payload["testing"], indent=2),
        "ad-studio-input.json": json.dumps(payload, indent=2),
        "activation-readme.md": readme,
        "package-manifest.json": json.dumps(manifest, indent=2),
    }


def make_activation_zip(project: dict[str, Any], audience: dict[str, Any], offer: str | None = None) -> tuple[bytes, str, dict[str, Any]]:
    payload = build_activation_payload(project, audience, offer)
    files = files_for_package(payload)
    filename = f"activation_{_slug(payload['campaign']['name'])}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.zip"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buffer.getvalue(), filename, payload
