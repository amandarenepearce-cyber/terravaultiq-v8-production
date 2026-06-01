from __future__ import annotations

import streamlit as st

from components.dashboard import render_dashboard
from components.forms import project_picker
from config.settings import settings
from core.auth import login_ui
from core.navigation import sidebar_nav
from core.session import init_session
from core.storage import list_projects, load_project
from modules import projects_ui
from modules.activation_studio.ui import render as render_activation
from modules.audience_builder.ui import render as render_audience_builder
from modules.geo_tool.ui import render as render_geo_tool
from modules.leadgen.ui import render as render_leadgen
from modules.lookback_intelligence.ui import render as render_lookback
from modules.reports.ui import render as render_reports

st.set_page_config(page_title=settings.app_name, page_icon="📍", layout="wide")
init_session()

if st.session_state.user is None:
    user = login_ui()
    if user:
        st.session_state.user = user
        st.rerun()
    st.stop()

user = st.session_state.user
st.sidebar.title("TerravaultIQ")
st.sidebar.caption(f"{user['name']} · {user['role']}")

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.session_state.active_project_id = None
    st.rerun()

projects = list_projects()
active_project_id = project_picker(projects)
if active_project_id:
    st.session_state.active_project_id = active_project_id

project = None
if st.session_state.active_project_id:
    project = load_project(st.session_state.active_project_id)

page = sidebar_nav(user["role"])

if page == "dashboard":
    render_dashboard()
elif page == "projects":
    projects_ui.render_projects(user)
elif page == "geo_tool":
    render_geo_tool(user, project)
elif page == "lookback":
    render_lookback(user, project)
elif page == "audience_builder":
    render_audience_builder(user, project)
elif page == "leadgen":
    render_leadgen(user, project)
elif page == "activation":
    render_activation(user, project)
elif page == "reports":
    render_reports(user, project)
elif page == "admin":
    st.title("Admin")
    st.write("Use this page for user controls, permissions, settings, and future white-label options.")
