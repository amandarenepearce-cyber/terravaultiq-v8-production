from __future__ import annotations

import streamlit as st


def metric_card(title: str, value: str, help_text: str = "") -> None:
    with st.container(border=True):
        st.subheader(title)
        st.markdown(f"## {value}")
        if help_text:
            st.caption(help_text)
