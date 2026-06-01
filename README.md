# TerravaultIQ V8 Scaffold

TerravaultIQ V8 is a Streamlit-based internal audience intelligence platform scaffold built to support both:
- one unified Core platform
- standalone modules that can later be sold separately

## Included in this zip
- TerravaultIQ Core shell
- Google OAuth-ready auth service with dev fallback login
- shared schema and JSON storage
- dashboard
- GEO Tool
- Lookback Intelligence
- Audience Builder MVP
- LeadGen
- Activation Studio scaffold
- Reports hub
- audit logging
- export center

## Important note about login
Google login is scaffolded and ready, but it will not work until you add your own OAuth credentials and redirect URI.

Until then, set `AUTH_MODE=dev` and use the built-in dev login.

## Quick start
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Environment variables
Create a `.env` file or configure your host secrets with:

```bash
AUTH_MODE=dev
APP_BASE_URL=http://localhost:8501
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8501
ALLOWED_EMAIL_DOMAIN=
ALLOWED_EMAILS=
ADMIN_EMAILS=
```

### Production auth
Set:
- `AUTH_MODE=google`
- valid Google OAuth credentials
- a matching redirect URI in Google Cloud Console

## Streamlit deploy checklist
1. Push code to Git.
2. Add secrets/environment variables to Streamlit Cloud or your host.
3. Set redirect URI in Google Cloud Console.
4. Redeploy.
5. Test admin, analyst, and viewer access.

## Folder overview
```text
terravaultiq_v8/
  app.py
  core/
  modules/
  components/
  config/
  utils/
  data/
```

## What is working now
- Dashboard shell
- Project creation and persistence
- Shared audience schema
- Audience Builder MVP
- Recommendation rules
- JSON/CSV export hub
- Audit logs
- Module placeholders wired into Core

## What still needs your live setup
- real Google OAuth credentials
- polished UI/branding
- production deployment
- external integrations and API layer
