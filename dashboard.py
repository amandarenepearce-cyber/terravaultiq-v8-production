from __future__ import annotations

import streamlit as st

from components.cards import metric_card
from core.storage import list_audit_events, list_export_records, list_projects


def render_dashboard() -> None:
    projects = list_projects()
    audits = list_audit_events(limit=50)
    exports = list_export_records()
    total_audiences = sum(len(p.get("audiences", [])) for p in projects)
    total_warnings = sum(1 for p in projects for a in p.get("audiences", []) if a.get("warning_status") == "warning")

    st.title("TerravaultIQ Command Center")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Active Projects", str(len(projects)))
    with col2:
        metric_card("Saved Audiences", str(total_audiences))
    with col3:
        metric_card("Warnings", str(total_warnings))
    with col4:
        metric_card("Exports", str(len(exports)))

    st.subheader("Recommended Next Actions")
    if total_warnings:
        st.warning("Some audiences are below the recommended threshold. Review Audience Builder or widen your radius/date windows.")
    else:
        st.success("No critical warning queues right now.")

    st.subheader("Recent Audit Activity")
    if audits:
        for item in audits[:10]:
            st.markdown(f"- **{item.get('event_type')}** · {item.get('event_summary')} · `{item.get('timestamp')}`")
    else:
        st.info("No audit events yet.")
