from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path
from typing import Any

from config.settings import EXPORTS_DIR

AUDIENCE_CSV_COLUMNS = [
    "audience_id",
    "audience_name",
    "location_input",
    "radius_value",
    "radius_unit",
    "start_date",
    "end_date",
    "estimated_audience_size",
    "customer_mode",
    "campaign_name",
    "notes",
    "market_region",
    "channel",
    "created_by",
    "created_at",
    "context_mode",
]


def audience_to_csv_text(audience: dict[str, Any]) -> str:
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=AUDIENCE_CSV_COLUMNS)
    writer.writeheader()
    writer.writerow({key: audience.get(key, "") for key in AUDIENCE_CSV_COLUMNS})
    return buffer.getvalue()


def write_export_file(filename: str, content: str) -> Path:
    path = EXPORTS_DIR / filename
    path.write_text(content)
    return path


def audience_to_json_text(audience: dict[str, Any]) -> str:
    return json.dumps(audience, indent=2)
