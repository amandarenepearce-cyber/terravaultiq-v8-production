from __future__ import annotations

import os
from typing import Any

import streamlit as st
from authlib.integrations.requests_client import OAuth2Session

from config.roles import ROLE_OPTIONS
from config.settings import settings


def _infer_role(email: str) -> str:
    email = (email or "").lower()
    if email in settings.admin_emails:
        return "admin"
    return "analyst"


def _allowed_email(email: str) -> bool:
    email = (email or "").lower()
    if settings.allowed_emails and email in settings.allowed_emails:
        return True
    if settings.allowed_email_domain and email.endswith("@" + settings.allowed_email_domain.lower()):
        return True
    return settings.auth_mode == "dev"


def login_ui() -> dict[str, Any] | None:
    st.title("TerravaultIQ Login")
    st.caption("Use dev login tonight, then switch to Google OAuth when you add your production credentials.")

    if settings.auth_mode == "google":
        return _google_login_ui()
    return _dev_login_ui()


def _dev_login_ui() -> dict[str, Any] | None:
    with st.form("dev_login"):
        email = st.text_input("Email", value=os.getenv("DEV_LOGIN_EMAIL", "owner@example.com"))
        name = st.text_input("Name", value="TerravaultIQ User")
        role = st.selectbox("Role", ROLE_OPTIONS, index=0)
        submitted = st.form_submit_button("Login")
    if submitted:
        return {"email": email, "name": name, "role": role}
    return None


def _google_login_ui() -> dict[str, Any] | None:
    st.info("Google OAuth is enabled. Add your credentials and exact redirect URI in your environment/secrets.")
    code = st.query_params.get("code")
    if not settings.google_client_id or not settings.google_client_secret:
        st.error("Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET.")
        return None

    if not code:
        auth_url = _build_auth_url()
        st.link_button("Sign in with Google", auth_url)
        return None

    try:
        token = _exchange_code_for_token(str(code))
        user = _fetch_google_userinfo(token)
        email = user.get("email", "")
        if not _allowed_email(email):
            st.error("This email is not approved for access.")
            return None
        return {"email": email, "name": user.get("name", email), "role": _infer_role(email)}
    except Exception as exc:  # noqa: BLE001
        st.error(f"Google login failed: {exc}")
        return None


def _build_auth_url() -> str:
    client = OAuth2Session(settings.google_client_id, settings.google_client_secret, scope="openid email profile", redirect_uri=settings.google_redirect_uri)
    auth_url, _state = client.create_authorization_url("https://accounts.google.com/o/oauth2/v2/auth")
    return auth_url


def _exchange_code_for_token(code: str) -> dict[str, Any]:
    client = OAuth2Session(settings.google_client_id, settings.google_client_secret, redirect_uri=settings.google_redirect_uri)
    return client.fetch_token("https://oauth2.googleapis.com/token", code=code)


def _fetch_google_userinfo(token: dict[str, Any]) -> dict[str, Any]:
    client = OAuth2Session(settings.google_client_id, token=token)
    response = client.get("https://openidconnect.googleapis.com/v1/userinfo")
    response.raise_for_status()
    return response.json()
