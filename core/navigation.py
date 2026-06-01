from __future__ import annotations

import streamlit as st

from core.permissions import can_access

NAV_ITEMS = [
    ("dashboard", "Dashboard"),
    ("projects", "Projects"),
    ("geo_tool", "GEO Tool"),
    ("lookback", "Lookback Intelligence"),
    ("audience_builder", "Audience Builder"),
    ("leadgen", "LeadGen"),
    ("activation", "Activation Studio"),
    ("reports", "Reports"),
    ("admin", "Admin"),
]


def sidebar_nav(role: str) -> str:
    options = [label for key, label in NAV_ITEMS if can_access(role, key)]
    label_to_key = {label: key for key, label in NAV_ITEMS}
    choice = st.sidebar.radio("Navigate", options)
    return label_to_key[choice]
