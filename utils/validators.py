from __future__ import annotations


def coerce_radius(value: float) -> int:
    return max(1, int(round(value)))


def safe_text(value: str) -> str:
    return (value or "").strip()
