from __future__ import annotations

import streamlit as st


def render(user: dict, project: dict | None) -> None:
    st.title("Lookback Intelligence")
    if not project:
        st.info("Choose or create a project first.")
        return
    st.write("Review historical audience activity patterns and opportunity signals.")
    st.date_input("Start date", key="lookback_start")
    st.date_input("End date", key="lookback_end")
    st.selectbox("Pattern focus", ["mixed", "commuter", "event-driven", "weekend-heavy"], key="lookback_pattern")
    st.info("Use this scaffold to plug in your existing lookback logic.")
