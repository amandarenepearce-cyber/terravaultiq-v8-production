from __future__ import annotations

import streamlit as st


def project_picker(projects: list[dict]) -> str | None:
    if not projects:
        return None
    options = {f"{p.get('project_name', 'Untitled')} ({p.get('project_id')})": p.get("project_id") for p in projects}
    label = st.sidebar.selectbox("Active Project", list(options.keys()))
    return options[label]
