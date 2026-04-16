#!/usr/bin/env python3
"""
Максимально полная выгрузка данных по задаче (issue) Яндекс Трекера.
"""

import argparse
from datetime import datetime
from typing import Dict

from tracker_api_utils import api_call, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Выгрузка полной информации по issue (с комментариями)")
    parser.add_argument("--issue", required=True, help="Ключ задачи, например SVT-123")
    parser.add_argument("--output", default=None, help="JSON-файл результата")
    args = parser.parse_args()

    issue_key = args.issue.strip().upper()

    report: Dict[str, object] = {
        "entity_type": "issue",
        "requested_ref": issue_key,
        "collected_at": datetime.now().isoformat(timespec="seconds"),
        "calls": {},
    }

    report["calls"]["issue_v2"] = api_call("GET", f"/v2/issues/{issue_key}")
    report["calls"]["issue_v2_expanded"] = api_call(
        "GET",
        f"/v2/issues/{issue_key}",
        params={"expand": "attachments,comments,changelog,relations"},
    )
    report["calls"]["comments_v2"] = api_call("GET", f"/v2/issues/{issue_key}/comments", params={"expand": "all"})
    report["calls"]["links_v2"] = api_call("GET", f"/v2/issues/{issue_key}/links")
    report["calls"]["attachments_v2"] = api_call("GET", "/v2/attachments", params={"issue": issue_key})
    report["calls"]["changelog_v2"] = api_call("GET", f"/v2/issues/{issue_key}/changelog")
    report["calls"]["transitions_v2"] = api_call("GET", f"/v2/issues/{issue_key}/transitions")

    out = args.output or f"issue_{issue_key}_full.json"
    write_json(out, report)
    print(f"✅ Готово: {out}")


if __name__ == "__main__":
    main()
