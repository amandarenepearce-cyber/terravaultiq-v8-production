from **future** import annotations

from typing import Any

import streamlit as st

AUTHORIZED_USERS = {
"[amanda@midwesthorizons.com](mailto:amanda@midwesthorizons.com)": {
"name": "Amanda Pearce",
"role": "owner",
},
"[mike@midwesthorizons.com](mailto:mike@midwesthorizons.com)": {
"name": "Mike",
"role": "admin",
},
"[brady@midwesthorizons.com](mailto:brady@midwesthorizons.com)": {
"name": "Brady",
"role": "sales",
},
}

def _normalize_email(email: str) -> str:
return (email or "").strip().lower()

def login_ui() -> dict[str, Any] | None:
st.title("TerravaultIQ Login")
st.caption("Authorized Midwest Horizons team access only.")

```
with st.form("team_login"):
    email = st.text_input("Email")
    access_code = st.text_input("Access Code", type="password")
    submitted = st.form_submit_button("Login")

if not submitted:
    return None

normalized_email = _normalize_email(email)

# Temporary team access code.
# Change this before sharing widely.
expected_code = st.secrets.get("TERRAVAULTIQ_TEAM_ACCESS_CODE", "TVIQ-TEAM-2026")

if normalized_email not in AUTHORIZED_USERS:
    st.error("This email is not approved for TerraVaultIQ access.")
    return None

if access_code != expected_code:
    st.error("Invalid access code.")
    return None

user = AUTHORIZED_USERS[normalized_email]

return {
    "email": normalized_email,
    "name": user["name"],
    "role": user["role"],
}
```
