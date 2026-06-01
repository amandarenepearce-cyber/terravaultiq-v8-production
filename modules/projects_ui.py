from __future__ import annotations

import streamlit as st

from core.audit import log_event
from core.schema import Project, to_dict
from core.storage import list_projects, load_project, save_project
from utils.dates import utc_now_iso


def render_projects(user: dict) -> None:
    st.title("Projects")
    with st.form("create_project"):
        project_name = st.text_input("Project name")
        account_name = st.text_input("Account name")
        notes = st.text_area("Notes")
        tags = st.text_input("Tags (comma separated)")
        submitted = st.form_submit_button("Save Project")
    if submitted and project_name.strip():
        project = Project(
            project_name=project_name.strip(),
            account_name=account_name.strip(),
            created_by=user["email"],
            notes=notes.strip(),
            tags=[x.strip() for x in tags.split(",") if x.strip()],
        )
        save_project(to_dict(project))
        log_event(project.project_id, "project", project.project_id, "project_created", f"Created project {project.project_name}", user["email"], "projects")
        st.success("Project saved.")

    st.subheader("Saved Projects")
    for project in list_projects():
        with st.container(border=True):
            st.markdown(f"### {project.get('project_name', 'Untitled')}  ")
            st.caption(f"{project.get('project_id')} · {project.get('account_name', '')}")
            st.write(project.get("notes", ""))
            st.write(f"Audiences: {len(project.get('audiences', []))}")
            if st.button("Set Active", key=f"active_{project.get('project_id')}"):
                st.session_state.active_project_id = project.get("project_id")
                refreshed = load_project(project.get("project_id"))
                refreshed["updated_at"] = utc_now_iso()
                save_project(refreshed)
                st.success("Active project updated.")
