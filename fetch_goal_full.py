#!/usr/bin/env python3
"""
Максимально полная выгрузка данных по цели (goal) Яндекс Трекера.
"""

import argparse
from datetime import datetime
from typing import Any, Dict, Optional

from tracker_api_utils import api_call, write_json


def extract_first_item(data: Any) -> Optional[Dict[str, Any]]:
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    if isinstance(data, dict):
        for key in ("items", "values", "goals"):
            value = data.get(key)
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return value[0]
    return None


def resolve_goal(goal_ref: str) -> Dict[str, Any]:
    if goal_ref.isdigit():
        by_short = api_call("POST", "/v3/entities/goal/_search", payload={"filter": {"shortId": int(goal_ref)}})
        item = extract_first_item(by_short.get("data"))
        if item and item.get("id"):
            return {"goal_id": str(item["id"]), "goal_short_id": item.get("shortId"), "resolver_response": by_short}

    by_id = api_call("GET", f"/v3/entities/goal/{goal_ref}", params={"expand": "all"})
    if by_id.get("ok") and isinstance(by_id.get("data"), dict):
        data = by_id["data"]
        return {"goal_id": str(data.get("id") or goal_ref), "goal_short_id": data.get("shortId"), "resolver_response": by_id}

    by_key = api_call("POST", "/v3/entities/goal/_search", payload={"filter": {"key": goal_ref}})
    item = extract_first_item(by_key.get("data"))
    if item and item.get("id"):
        return {"goal_id": str(item["id"]), "goal_short_id": item.get("shortId"), "resolver_response": by_key}

    return {"goal_id": goal_ref, "goal_short_id": None, "resolver_response": by_id}


def main() -> None:
    parser = argparse.ArgumentParser(description="Выгрузка полной информации по goal (с комментариями)")
    parser.add_argument("--goal", required=True, help="goal reference: id, shortId или key")
    parser.add_argument("--output", default=None, help="JSON-файл результата")
    args = parser.parse_args()

    resolved = resolve_goal(args.goal)
    goal_id = resolved["goal_id"]
    short_id = resolved.get("goal_short_id")

    report: Dict[str, Any] = {
        "entity_type": "goal",
        "requested_ref": args.goal,
        "resolved": resolved,
        "collected_at": datetime.now().isoformat(timespec="seconds"),
        "calls": {},
    }

    report["calls"]["goal_v3"] = api_call("GET", f"/v3/entities/goal/{goal_id}", params={"expand": "all"})
    if short_id is not None:
        report["calls"]["goal_v2"] = api_call("GET", f"/v2/goals/{short_id}")
    else:
        report["calls"]["goal_v2"] = {"ok": False, "status_code": None, "data": {"error": "shortId not resolved"}}

    report["calls"]["comments_v3"] = api_call("GET", f"/v3/entities/goal/{goal_id}/comments", params={"expand": "all"})
    report["calls"]["relations_v3"] = api_call("GET", f"/v3/entities/goal/{goal_id}/relations")
    report["calls"]["checklist_v3"] = api_call("POST", f"/v3/entities/goal/{goal_id}/checklistItems", payload={})
    report["calls"]["attachments_v2"] = api_call("GET", "/v2/attachments", params={"entity": "goal", "entityId": goal_id})
    report["calls"]["links_v2"] = api_call("GET", "/v2/links", params={"entity": "goal", "entityId": goal_id})
    report["calls"]["changelog_v2"] = api_call("GET", f"/v2/entities/goal/{goal_id}/changelog")

    out = args.output or f"goal_{goal_id}_full.json"
    write_json(out, report)
    print(f"✅ Готово: {out}")


if __name__ == "__main__":
    main()
