from __future__ import annotations

ROLE_ACCESS = {
    "admin": {"dashboard", "projects", "geo_tool", "lookback", "audience_builder", "leadgen", "activation", "reports", "admin"},
    "analyst": {"dashboard", "projects", "geo_tool", "lookback", "audience_builder", "leadgen", "activation", "reports"},
    "sales": {"dashboard", "projects", "leadgen", "reports"},
    "viewer": {"dashboard", "reports"},
}


def can_access(role: str, module_key: str) -> bool:
    return module_key in ROLE_ACCESS.get(role, set())
