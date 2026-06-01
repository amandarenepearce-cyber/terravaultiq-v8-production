# TerraVaultIQ Supabase Deployment Notes

This build is ready for private in-house testing. It still uses local JSON storage by default. For Supabase, move these storage areas into tables:

- projects
- audiences
- lead_runs
- exports
- audit_events
- app_settings / api_keys
- users / roles

## Recommended Supabase tables

### projects
- project_id text primary key
- project_name text
- account_name text
- notes text
- tags text[]
- created_at timestamptz
- updated_at timestamptz

### audiences
- audience_id text primary key
- project_id text references projects(project_id)
- payload jsonb
- created_at timestamptz
- updated_at timestamptz

### exports
- export_id text primary key
- project_id text
- audience_id text
- type text
- file_name text
- payload jsonb
- generated_at timestamptz

### app_settings
- setting_key text primary key
- setting_value text encrypted/server-side only
- updated_at timestamptz

## API key rule
Do not expose API keys in Streamlit widgets for normal users. Store keys in Supabase secrets, Streamlit secrets, or encrypted server-side settings. Show only masked values to admins.

## Suggested environment variables
See `.env.example`.
