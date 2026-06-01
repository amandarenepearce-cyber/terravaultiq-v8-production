from __future__ import annotations


def nice_label(value: str) -> str:
    return value.replace("_", " ").strip().title()
