from __future__ import annotations

from core.schema import AuditEvent, to_dict
from core.storage import append_audit_event


def log_event(project_id: str, entity_type: str, entity_id: str, event_type: str, summary: str, actor: str, module_name: str) -> None:
    event = AuditEvent(
        project_id=project_id,
        entity_type=entity_type,
        entity_id=entity_id,
        event_type=event_type,
        event_summary=summary,
        actor=actor,
        module_name=module_name,
    )
    append_audit_event(to_dict(event))
