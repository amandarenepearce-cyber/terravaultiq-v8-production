from __future__ import annotations

import streamlit as st


def render(user: dict, project: dict | None) -> None:
    st.title("GEO Tool")
    st.caption("Module scaffold wired into TerravaultIQ Core.")
    if not project:
        st.info("Choose or create a project first.")
        return
    st.write("Use this page to normalize market locations, set radii, and define geo boundaries.")
    st.text_input("Location or place", key="geo_location")
    st.slider("Radius (miles)", 1, 100, 10, key="geo_radius")
    st.selectbox("Boundary type", ["radius", "zip cluster", "custom market"], key="geo_boundary")
    st.success("This module is wired and ready for deeper logic.")
