from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config.settings import EXPORTS_DIR, LOGS_DIR, PROJECTS_DIR


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def list_projects() -> list[dict[str, Any]]:
    items = []
    for path in sorted(PROJECTS_DIR.glob("*.json")):
        project = _read_json(path, {})
        if project:
            items.append(project)
    return sorted(items, key=lambda x: x.get("updated_at", ""), reverse=True)


def save_project(project: dict[str, Any]) -> Path:
    path = PROJECTS_DIR / f"{project['project_id']}.json"
    existing = _read_json(path, {})
    existing.update(project)
    _write_json(path, existing)
    return path


def load_project(project_id: str) -> dict[str, Any]:
    path = PROJECTS_DIR / f"{project_id}.json"
    return _read_json(path, {})


def save_audience(project_id: str, audience: dict[str, Any]) -> Path:
    project = load_project(project_id)
    audiences = project.get("audiences", [])
    audiences = [a for a in audiences if a.get("audience_id") != audience.get("audience_id")]
    audiences.append(audience)
    project["audiences"] = audiences
    save_project(project)
    return PROJECTS_DIR / f"{project_id}.json"


def list_audiences(project_id: str) -> list[dict[str, Any]]:
    return load_project(project_id).get("audiences", [])


def save_export_record(record: dict[str, Any]) -> Path:
    path = EXPORTS_DIR / f"{record['export_id']}.json"
    _write_json(path, record)
    return path


def list_export_records() -> list[dict[str, Any]]:
    items = []
    for path in sorted(EXPORTS_DIR.glob("*.json")):
        obj = _read_json(path, {})
        if obj:
            items.append(obj)
    return sorted(items, key=lambda x: x.get("generated_at", ""), reverse=True)


def append_audit_event(event: dict[str, Any]) -> Path:
    path = LOGS_DIR / "audit_log.json"
    events = _read_json(path, [])
    events.append(event)
    _write_json(path, events)
    return path


def list_audit_events(limit: int = 200) -> list[dict[str, Any]]:
    path = LOGS_DIR / "audit_log.json"
    events = _read_json(path, [])
    return list(reversed(events[-limit:]))
