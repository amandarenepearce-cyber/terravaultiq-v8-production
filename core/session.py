from __future__ import annotations

import streamlit as st


def init_session() -> None:
    defaults = {
        "user": None,
        "active_project_id": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
