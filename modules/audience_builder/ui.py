from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from core.audit import log_event
from core.exports import audience_to_csv_text, audience_to_json_text, write_export_file
from core.schema import ExportRecord, to_dict
from core.storage import list_audiences, save_audience, save_export_record
from modules.audience_builder.logic import build_audience


def render(user: dict, project: dict | None) -> None:
    st.title("Audience Builder")
    if not project:
        st.info("Choose or create a project first.")
        return

    with st.form("audience_builder"):
        audience_name = st.text_input("Audience name")
        location_input = st.text_input("Location input")
        radius_value = st.slider("Radius (miles)", 1, 100, 5)
        start_date = st.date_input("Start date", value=date.today() - timedelta(days=7))
        end_date = st.date_input("End date", value=date.today())
        customer_mode = st.selectbox("Customer mode", ["include", "exclude", "ignore"], index=2)
        campaign_name = st.text_input("Campaign name")
        notes = st.text_area("Notes")
        market_region = st.text_input("Market region")
        channel = st.selectbox("Channel", ["display", "meta", "search", "email", "sms", "other"])
        confidence = st.selectbox("Confidence", ["low", "medium", "high"], index=1)
        location_type = st.selectbox("Location type", ["unknown", "retail", "venue", "stadium", "downtown", "neighborhood"])
        density_pattern = st.selectbox("Density pattern", ["mixed", "event-driven", "commuter", "weekend-heavy", "steady"])
        peak_activity_window = st.text_input("Peak activity window", value="fri-sun evenings")
        submitted = st.form_submit_button("Build audience")

    if submitted and audience_name.strip() and location_input.strip():
        audience = build_audience(
            {
                "audience_name": audience_name.strip(),
                "project_id": project["project_id"],
                "location_input": location_input.strip(),
                "radius_value": radius_value,
                "start_date": start_date,
                "end_date": end_date,
                "customer_mode": customer_mode,
                "campaign_name": campaign_name.strip(),
                "notes": notes.strip(),
                "market_region": market_region.strip(),
                "channel": channel,
                "confidence": confidence,
                "location_type": location_type,
                "density_pattern": density_pattern,
                "peak_activity_window": peak_activity_window.strip(),
                "created_by": user["email"],
            }
        )
        save_audience(project["project_id"], audience)
        log_event(project["project_id"], "audience", audience["audience_id"], "audience_created", f"Created audience {audience['audience_name']}", user["email"], "audience_builder")
        log_event(project["project_id"], "audience", audience["audience_id"], "estimate_run", f"Ran estimate for {audience['audience_name']}", user["email"], "audience_builder")
        st.success("Audience saved.")

    audiences = list_audiences(project["project_id"])
    if audiences:
        st.subheader("Saved audiences")
        selected = st.selectbox("Choose audience", audiences, format_func=lambda x: f"{x['audience_name']} · {x['audience_id']}")
        st.json(selected)
        cols = st.columns(2)
        with cols[0]:
            if st.button("Export audience JSON"):
                filename = f"{selected['audience_id']}.json"
                path = write_export_file(filename, audience_to_json_text(selected))
                save_export_record(to_dict(ExportRecord(project_id=project["project_id"], audience_id=selected["audience_id"], export_type="json", file_name=path.name, generated_by=user["email"])))
                log_event(project["project_id"], "audience", selected["audience_id"], "audience_exported", f"Exported audience JSON {path.name}", user["email"], "audience_builder")
                st.success(f"Wrote {path.name}")
        with cols[1]:
            if st.button("Export audience CSV"):
                filename = f"{selected['audience_id']}.csv"
                path = write_export_file(filename, audience_to_csv_text(selected))
                save_export_record(to_dict(ExportRecord(project_id=project["project_id"], audience_id=selected["audience_id"], export_type="csv", file_name=path.name, generated_by=user["email"])))
                log_event(project["project_id"], "audience", selected["audience_id"], "audience_exported", f"Exported audience CSV {path.name}", user["email"], "audience_builder")
                st.success(f"Wrote {path.name}")
