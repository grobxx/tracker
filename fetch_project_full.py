#!/usr/bin/env python3
"""
Максимально полная выгрузка данных по проекту Яндекс Трекера.
"""

import argparse
from datetime import datetime
from typing import Any, Dict

from tracker_api_utils import api_call, write_json


def resolve_project(project_ref: str) -> Dict[str, Any]:
    by_v2 = api_call("GET", f"/v2/projects/{project_ref}", params={"expand": "queues"})
    if by_v2.get("ok") and isinstance(by_v2.get("data"), dict):
        data = by_v2["data"]
        resolved_id = data.get("id") or project_ref
        resolved_key = data.get("key") or project_ref
        return {"project_id": str(resolved_id), "project_key": resolved_key, "resolver_response": by_v2}
    return {"project_id": project_ref, "project_key": project_ref, "resolver_response": by_v2}


def main() -> None:
    parser = argparse.ArgumentParser(description="Выгрузка полной информации по project (с комментариями)")
    parser.add_argument("--project", required=True, help="project reference: id или key")
    parser.add_argument("--output", default=None, help="JSON-файл результата")
    args = parser.parse_args()

    resolved = resolve_project(args.project)
    project_id = resolved["project_id"]
    project_key = resolved["project_key"]

    report: Dict[str, Any] = {
        "entity_type": "project",
        "requested_ref": args.project,
        "resolved": resolved,
        "collected_at": datetime.now().isoformat(timespec="seconds"),
        "calls": {},
    }

    report["calls"]["project_v2"] = api_call("GET", f"/v2/projects/{project_key}", params={"expand": "queues"})
    report["calls"]["project_v3"] = api_call("GET", f"/v3/entities/project/{project_id}", params={"expand": "all"})
    report["calls"]["comments_v3"] = api_call("GET", f"/v3/entities/project/{project_id}/comments", params={"expand": "all"})
    report["calls"]["relations_v3"] = api_call("GET", f"/v3/entities/project/{project_id}/relations")
    report["calls"]["checklist_v3"] = api_call("POST", f"/v3/entities/project/{project_id}/checklistItems", payload={})
    report["calls"]["attachments_v2"] = api_call("GET", "/v2/attachments", params={"entity": "project", "entityId": project_id})
    report["calls"]["links_v2"] = api_call("GET", "/v2/links", params={"entity": "project", "entityId": project_id})
    report["calls"]["changelog_v2"] = api_call("GET", f"/v2/entities/project/{project_id}/changelog")

    out = args.output or f"project_{project_key}_full.json"
    write_json(out, report)
    print(f"✅ Готово: {out}")


if __name__ == "__main__":
    main()
