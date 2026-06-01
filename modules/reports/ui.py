from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
import streamlit as st

from core.storage import list_audit_events, list_export_records, load_project


def _safe_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def render(user: dict, project: dict | None) -> None:
    st.title('Reports')
    exports = list_export_records()
    audits = list_audit_events(limit=100)

    if project:
        latest = load_project(project['project_id'])
        audiences = latest.get('audiences', [])
        lead_runs = latest.get('lead_runs', [])

        st.subheader('Project summary')
        st.write(f"Project: **{latest.get('project_name')}**")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric('Saved audiences', len(audiences))
        m2.metric('Lead searches', len(lead_runs))
        m3.metric('Latest lead count', lead_runs[-1].get('row_count', 0) if lead_runs else 0)
        m4.metric('Exports', len(exports))

        summary = {
            'project': latest.get('project_name'),
            'audience_count': len(audiences),
            'lead_run_count': len(lead_runs),
            'latest_lead_count': lead_runs[-1].get('row_count', 0) if lead_runs else 0,
            'warning_count': sum(1 for a in audiences if a.get('warning_status') == 'warning'),
            'strong_count': sum(1 for a in audiences if a.get('score_label') == 'strong'),
            'generated_at': datetime.now().isoformat(),
        }
        st.download_button('Download project summary JSON', data=json.dumps(summary, indent=2), file_name=f"project_summary_{project['project_id']}.json", mime='application/json')

        if audiences:
            st.subheader('Saved audiences')
            audience_df = pd.DataFrame(audiences)
            cols = [c for c in ['audience_name', 'estimated_audience_size', 'score', 'score_label', 'warning_status', 'channel'] if c in audience_df.columns]
            st.dataframe(audience_df[cols], use_container_width=True)

        st.subheader('Lead search reports')
        if lead_runs:
            run_options = {f"{r.get('generated_at', '')} · {r.get('meta', {}).get('keyword', '')} · {r.get('row_count', 0)} rows": r for r in reversed(lead_runs)}
            selected_label = st.selectbox('Choose lead run', list(run_options.keys()))
            selected = run_options[selected_label]
            rows = selected.get('rows', [])
            df = _safe_df(rows)
            st.json({'run_id': selected.get('run_id'), 'meta': selected.get('meta', {}), 'row_count': selected.get('row_count', 0)})
            if not df.empty:
                preview_cols = [c for c in ['name', 'business_type', 'address', 'website', 'primary_email', 'primary_phone', 'needs_leads_score', 'needs_leads_tier'] if c in df.columns]
                st.dataframe(df[preview_cols] if preview_cols else df, use_container_width=True, hide_index=True, height=460)
                stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                st.download_button('Download selected lead report CSV', data=df.to_csv(index=False).encode('utf-8'), file_name=f'lead_report_{stamp}.csv', mime='text/csv')
        else:
            st.info('No lead searches saved yet. Run LeadGen first.')
    else:
        st.info('Choose a project to see a project-level summary.')

    st.subheader('Exports')
    if exports:
        st.dataframe(pd.DataFrame(exports), use_container_width=True)
    else:
        st.info('No exports yet.')

    st.subheader('Audit log')
    if audits:
        st.dataframe(pd.DataFrame(audits), use_container_width=True)
    else:
        st.info('No audit events yet.')
