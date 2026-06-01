from __future__ import annotations

import io
import json
import os
import zipfile
from datetime import datetime

import pandas as pd
import streamlit as st

from core.audit import log_event
from core.storage import load_project, save_project
from modules.discovery import discover_businesses, expand_topic_queries, search_public_topics
from modules.enrichment import enrich_rows
from modules.scoring import score_rows
from modules import packager as packager_mod
from modules import legacy_exports as exports_mod


def _normalize_zip_list(text: str) -> list[str]:
    normalizer = getattr(packager_mod, 'normalize_zip_list', None)
    if callable(normalizer):
        return normalizer(text)
    return [p.strip() for p in str(text or '').replace('\n', ',').split(',') if p.strip()]


def _dedupe_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    work = df.copy()
    for col in ['name', 'address', 'website', 'phone']:
        if col not in work.columns:
            work[col] = ''
    work['_dedupe_name'] = work['name'].astype(str).str.strip().str.lower()
    work['_dedupe_address'] = work['address'].astype(str).str.strip().str.lower()
    work['_dedupe_website'] = work['website'].astype(str).str.strip().str.lower()
    work['_dedupe_phone'] = work['phone'].astype(str).str.strip().str.lower()
    work = work.drop_duplicates(subset=['_dedupe_name', '_dedupe_address', '_dedupe_website', '_dedupe_phone'], keep='first')
    return work.drop(columns=['_dedupe_name', '_dedupe_address', '_dedupe_website', '_dedupe_phone'], errors='ignore').reset_index(drop=True)


def _sort_by_score(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.reset_index(drop=True)
    score_col = 'needs_leads_score' if 'needs_leads_score' in df.columns else 'lead_score' if 'lead_score' in df.columns else None
    if not score_col:
        return df.reset_index(drop=True)
    work = df.copy()
    work['_score_num'] = pd.to_numeric(work[score_col], errors='coerce').fillna(-1)
    return work.sort_values('_score_num', ascending=False).drop(columns=['_score_num'], errors='ignore').reset_index(drop=True)


def _count_present(df: pd.DataFrame, col: str) -> int:
    if col not in df.columns:
        return 0
    return int(df[col].astype(str).fillna('').str.strip().ne('').sum())


def _hot_count(df: pd.DataFrame) -> int:
    col = 'needs_leads_score' if 'needs_leads_score' in df.columns else 'lead_score' if 'lead_score' in df.columns else None
    if not col:
        return 0
    return int((pd.to_numeric(df[col], errors='coerce').fillna(0) >= 75).sum())


def _excel_bytes(df: pd.DataFrame) -> bytes:
    exporter = getattr(exports_mod, 'dataframe_to_excel_bytes', None)
    if callable(exporter):
        try:
            return exporter(df)
        except Exception:
            pass
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Leads')
    out.seek(0)
    return out.read()


def _client_export_df(df: pd.DataFrame) -> pd.DataFrame:
    fn = getattr(packager_mod, 'build_client_export_df', None)
    if callable(fn):
        try:
            return fn(df)
        except Exception:
            pass
    preferred = ['name','business_type','search_keyword','source_zip','address','website','site_live','final_url','primary_email','secondary_email','email_found','email_source_url','email_confidence','contact_page_url','contact_form_found','pages_scanned','scan_error','primary_phone','phone','rating','ratings_total','needs_leads_score','needs_leads_tier','needs_leads_reason','ad_presence_status','pitch_opening_line','pitch_offer','pitch_cta']
    cols = [c for c in preferred if c in df.columns]
    return df[cols + [c for c in df.columns if c not in cols]].copy()


def _crm_export_df(df: pd.DataFrame) -> pd.DataFrame:
    fn = getattr(packager_mod, 'build_crm_export_df', None)
    if callable(fn):
        try:
            return fn(df)
        except Exception:
            pass
    out = pd.DataFrame()
    out['name'] = df['name'] if 'name' in df.columns else ''
    out['primary_email'] = df['primary_email'] if 'primary_email' in df.columns else ''
    out['primary_phone'] = df['primary_phone'] if 'primary_phone' in df.columns else (df['phone'] if 'phone' in df.columns else '')
    out['email_source_url'] = df['email_source_url'] if 'email_source_url' in df.columns else ''
    out['contact_page_url'] = df['contact_page_url'] if 'contact_page_url' in df.columns else ''
    out['website'] = df['website'] if 'website' in df.columns else ''
    out['status'] = 'new'
    out['priority'] = df['needs_leads_tier'] if 'needs_leads_tier' in df.columns else ''
    out['owner'] = ''
    out['notes'] = df['needs_leads_reason'] if 'needs_leads_reason' in df.columns else ''
    return out


def _package_zip(client_df: pd.DataFrame, crm_df: pd.DataFrame, summary_text: str, manifest: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('client_leads.csv', client_df.to_csv(index=False).encode('utf-8'))
        zf.writestr('crm_import.csv', crm_df.to_csv(index=False).encode('utf-8'))
        zf.writestr('package_summary.txt', summary_text.encode('utf-8'))
        zf.writestr('manifest.json', json.dumps(manifest, indent=2))
    buf.seek(0)
    return buf.read()


def _save_lead_run(project_id: str, df: pd.DataFrame, meta: dict) -> None:
    project_latest = load_project(project_id)
    runs = project_latest.get('lead_runs', [])
    run = {
        'run_id': f"leadrun_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        'generated_at': datetime.now().isoformat(),
        'meta': meta,
        'row_count': int(len(df)),
        'rows': json.loads(df.to_json(orient='records')),
    }
    runs.append(run)
    project_latest['lead_runs'] = runs[-10:]
    save_project(project_latest)


def _latest_lead_df(project: dict) -> tuple[pd.DataFrame, dict]:
    runs = project.get('lead_runs', []) if project else []
    if not runs:
        return pd.DataFrame(), {}
    latest = runs[-1]
    return pd.DataFrame(latest.get('rows', [])), latest.get('meta', {})


def render(user: dict, project: dict | None) -> None:
    st.title('LeadGen')
    st.caption('Find, enrich, score, report, and package prospects. This restores the working v7 engine inside the v8 app shell.')

    if not project:
        st.info('Choose or create a project first.')
        return

    st.session_state.setdefault('leadgen_results_df', pd.DataFrame())
    st.session_state.setdefault('leadgen_last_meta', {})

    tab_search, tab_package = st.tabs(['Find leads', 'Build client package'])

    with tab_search:
        left, right = st.columns([2.2, 1], gap='large')
        with left:
            scan_mode = st.radio('Scan Mode', ['Single ZIP Deep Scan', 'Multi-ZIP Area Scan'], index=1, horizontal=True)
            if scan_mode == 'Single ZIP Deep Scan':
                zip_code = st.text_input('ZIP CODE', value='66048')
                zip_list_text = ''
            else:
                zip_code = ''
                zip_list_text = st.text_area('ZIP LIST', value='66048, 66044, 66086', height=100)
            radius = st.number_input('RADIUS (miles)', min_value=1, max_value=100, value=10, step=1)
            area_label = st.text_input('CITY / AREA LABEL', value=project.get('account_name') or project.get('project_name') or 'Leavenworth')
            search_mode = st.selectbox('Search Mode', ['Marketing Prospect Finder', 'Custom Business Search', 'Public Intent Search', 'Relocation Interest Finder', 'Community Interest Finder'])
            label = 'INDUSTRY / CATEGORY' if search_mode == 'Marketing Prospect Finder' else 'CATEGORY / TOPIC / KEYWORD'
            keyword = st.text_input(label, value='roofing')
            if search_mode in ['Public Intent Search', 'Relocation Interest Finder', 'Community Interest Finder']:
                with st.expander('Suggested public search phrases'):
                    for phrase in expand_topic_queries(search_mode, keyword, zip_code=zip_code, area_label=area_label):
                        st.code(phrase, language=None)
            run_search = st.button('FIND LEADS', type='primary', use_container_width=True)

        with right:
            default_google_key = os.getenv('GOOGLE_PLACES_API_KEY', '') or os.getenv('GOOGLE_SEARCH_API_KEY', '')
            if default_google_key and not st.session_state.get('google_api_key'):
                st.session_state['google_api_key'] = default_google_key
            st.text_input('Google API Key', type='password', key='google_api_key', help='Required for Google Places business searches. Uses GOOGLE_PLACES_API_KEY from secrets/env when available.')
            use_google = st.checkbox('Use Google API if available', value=True)
            use_osm = st.checkbox('Use OpenStreetMap backup', value=False, help='Placeholder from v7. Google is the active provider in this build.')
            do_enrich = st.checkbox('Find website emails/contact pages', value=True, help='Scans homepage plus contact/about/team/staff/location fallback pages for public emails, contact forms, phones, and source URLs. Slower but stronger.')
            enrich_limit = st.number_input('Max rows to enrich', min_value=0, max_value=5000, value=250, step=25)
            do_score = st.checkbox('Score business leads', value=True)
            trim_results = st.checkbox('Trim final results', value=True)
            final_cap = st.selectbox('Final result cap', [100, 250, 500, 1000], index=1)
            max_pages = st.slider('Public search pages', 1, 5, 2)

        if run_search:
            try:
                zips = [zip_code.strip()] if scan_mode == 'Single ZIP Deep Scan' and zip_code.strip() else _normalize_zip_list(zip_list_text)
                all_rows: list[dict] = []
                if search_mode in ['Marketing Prospect Finder', 'Custom Business Search']:
                    if not zips:
                        st.error('Please enter at least one ZIP code.')
                    elif use_google and not st.session_state.get('google_api_key', '').strip():
                        st.error('Paste a Google API key before running a business search.')
                    else:
                        mode = 'marketing' if search_mode == 'Marketing Prospect Finder' else 'custom'
                        progress = st.progress(0, text='Searching businesses...')
                        for idx, z in enumerate(zips):
                            rows = discover_businesses(z, float(radius), mode, keyword.strip(), use_google, use_osm)
                            for row in rows:
                                row.update({'search_mode': search_mode, 'search_keyword': keyword.strip(), 'source_zip': z, 'area_label': area_label.strip()})
                            all_rows.extend(rows)
                            progress.progress((idx + 1) / len(zips), text=f'Business search {idx + 1}/{len(zips)}')
                        progress.empty()
                else:
                    target_zips = zips if zips else ['']
                    progress = st.progress(0, text='Searching public pages...')
                    for idx, z in enumerate(target_zips):
                        rows = search_public_topics(search_mode, keyword.strip(), z, area_label.strip(), max_pages, use_google, True)
                        for row in rows:
                            row.update({'search_mode': search_mode, 'search_keyword': keyword.strip(), 'source_zip': z, 'area_label': area_label.strip()})
                        all_rows.extend(rows)
                        progress.progress((idx + 1) / len(target_zips), text=f'Public search {idx + 1}/{len(target_zips)}')
                    progress.empty()

                if not all_rows:
                    st.warning('No results found. Check the Google API key, ZIPs, and category. Try a clear category like roofing, med spa, mortgage lenders, or house cleaners.')
                else:
                    if do_enrich:
                        limit = min(len(all_rows), int(enrich_limit))
                        if limit:
                            st.info(f'Enriching {limit} rows...')
                            all_rows = enrich_rows(all_rows[:limit]) + all_rows[limit:]
                    if do_score:
                        all_rows = score_rows(all_rows)
                    df = _sort_by_score(_dedupe_dataframe(pd.DataFrame(all_rows)))
                    if trim_results:
                        df = df.head(int(final_cap)).copy()
                    meta = {'search_mode': search_mode, 'keyword': keyword.strip(), 'area_label': area_label.strip(), 'scan_mode': scan_mode, 'radius': radius, 'run_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    st.session_state.leadgen_results_df = df
                    st.session_state.leadgen_last_meta = meta
                    _save_lead_run(project['project_id'], df, meta)
                    log_event(project['project_id'], 'lead_run', meta['run_at'], 'lead_search_completed', f"Found {len(df)} leads for {keyword.strip()}", user['email'], 'leadgen')
                    st.success(f'Found {len(df)} results.')
            except Exception as exc:
                st.error(f'Lead search failed: {exc}')

        df = st.session_state.leadgen_results_df
        if df.empty:
            latest_project = load_project(project['project_id'])
            df, meta = _latest_lead_df(latest_project)
            if not df.empty:
                st.session_state.leadgen_results_df = df
                st.session_state.leadgen_last_meta = meta
        if not df.empty:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric('Total Results', len(df))
            c2.metric('With Website', _count_present(df, 'website'))
            c3.metric('With Email', _count_present(df, 'primary_email'))
            c4.metric('Hot Leads', _hot_count(df))
            if 'email_found' in df.columns:
                st.caption(f"Email enrichment: {_count_present(df, 'primary_email')} emails found. Check primary_email, email_source_url, contact_page_url, contact_form_found, pages_scanned, and scan_error columns.")
            st.dataframe(df, use_container_width=True, hide_index=True, height=520)
            stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            d1, d2 = st.columns(2)
            d1.download_button('Download Search Results CSV', data=df.to_csv(index=False).encode('utf-8'), file_name=f'search_results_{stamp}.csv', mime='text/csv', use_container_width=True)
            d2.download_button('Download Search Results Excel', data=_excel_bytes(df), file_name=f'search_results_{stamp}.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', use_container_width=True)

    with tab_package:
        latest_project = load_project(project['project_id'])
        df = st.session_state.leadgen_results_df
        if df.empty:
            df, meta = _latest_lead_df(latest_project)
        else:
            meta = st.session_state.leadgen_last_meta
        if df.empty:
            st.info('Run a lead search first, then build a client package here.')
            return
        df = _sort_by_score(df)
        c1, c2, c3 = st.columns(3)
        package_name = c1.text_input('Package Name', value=f"{project.get('project_name', 'MWH')} Hot Lead Package")
        prepared_by = c2.text_input('Prepared By', value=user.get('name', 'Amanda'))
        max_rows = c3.number_input('Max Leads in Package', min_value=1, max_value=max(1, len(df)), value=min(250, len(df)), step=1)
        package_df = df.head(int(max_rows)).copy()
        client_df = _client_export_df(package_df)
        crm_df = _crm_export_df(package_df)
        summary_text = f"Package: {package_name}\nPrepared by: {prepared_by}\nRows: {len(package_df)}\nSearch mode: {meta.get('search_mode','')}\nKeyword: {meta.get('keyword','')}\nArea label: {meta.get('area_label','')}\nGenerated: {datetime.now().isoformat()}\n"
        manifest = {'package_name': package_name, 'prepared_by': prepared_by, 'generated_at': datetime.now().isoformat(), 'total_rows': int(len(package_df)), **meta}
        st.text_area('Package Summary', value=summary_text, height=180)
        st.dataframe(package_df, use_container_width=True, hide_index=True, height=420)
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        d1, d2, d3, d4 = st.columns(4)
        d1.download_button('Client CSV', data=client_df.to_csv(index=False).encode('utf-8'), file_name=f'client_leads_{stamp}.csv', mime='text/csv', use_container_width=True)
        d2.download_button('CRM CSV', data=crm_df.to_csv(index=False).encode('utf-8'), file_name=f'crm_import_{stamp}.csv', mime='text/csv', use_container_width=True)
        d3.download_button('Client Excel', data=_excel_bytes(client_df), file_name=f'client_leads_{stamp}.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', use_container_width=True)
        d4.download_button('Full ZIP', data=_package_zip(client_df, crm_df, summary_text, manifest), file_name=f'client_package_{stamp}.zip', mime='application/zip', use_container_width=True)
