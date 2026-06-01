from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PROJECTS_DIR = DATA_DIR / "projects"
EXPORTS_DIR = DATA_DIR / "exports"
LOGS_DIR = DATA_DIR / "logs"

for folder in [DATA_DIR, PROJECTS_DIR, EXPORTS_DIR, LOGS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

@dataclass(frozen=True)
class Settings:
    app_name: str = "TerravaultIQ"
    auth_mode: str = os.getenv("AUTH_MODE", "dev").lower()
    app_base_url: str = os.getenv("APP_BASE_URL", "http://localhost:8501")
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    google_redirect_uri: str = os.getenv("GOOGLE_REDIRECT_URI", os.getenv("APP_BASE_URL", "http://localhost:8501"))
    allowed_email_domain: str = os.getenv("ALLOWED_EMAIL_DOMAIN", "")
    allowed_emails: tuple[str, ...] = tuple(x.strip().lower() for x in os.getenv("ALLOWED_EMAILS", "").split(",") if x.strip())
    admin_emails: tuple[str, ...] = tuple(x.strip().lower() for x in os.getenv("ADMIN_EMAILS", "").split(",") if x.strip())

settings = Settings()
