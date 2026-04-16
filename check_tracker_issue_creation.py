#!/usr/bin/env python3
"""
Проверка возможности создания задач в Яндекс Трекере.

По умолчанию:
1) Проверяет, что очередь доступна.
2) Пытается создать тестовую задачу в указанной очереди (по умолчанию SVT).
3) Печатает структурированный результат и сохраняет JSON-отчёт.
"""

import os
import json
import argparse
from datetime import datetime
from typing import Any, Dict, Tuple

import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TRACKER_TOKEN")
ORG_ID = os.getenv("TRACKER_ORG_ID")
BASE_URL = "https://api.tracker.yandex.net"

if not TOKEN or not ORG_ID:
    print("❌ Ошибка: TRACKER_TOKEN или TRACKER_ORG_ID не найдены в .env")
    raise SystemExit(1)

HEADERS = {
    "Authorization": f"OAuth {TOKEN}",
    "X-Org-ID": ORG_ID,
    "Content-Type": "application/json",
}


def safe_json(response: requests.Response) -> Any:
    try:
        return response.json()
    except Exception:
        return {"raw": response.text[:2000]}


def check_queue(queue_key: str) -> Tuple[int, Any]:
    url = f"{BASE_URL}/v2/queues/{queue_key}"
    response = requests.get(url, headers=HEADERS)
    return response.status_code, safe_json(response)


def create_test_issue(queue_key: str) -> Tuple[int, Any]:
    url = f"{BASE_URL}/v2/issues/"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    payload: Dict[str, Any] = {
        "queue": queue_key,
        "summary": f"[TEST] Проверка создания задачи API ({now})",
        "description": (
            "Техническая тестовая задача, создана скриптом "
            "`check_tracker_issue_creation.py` для проверки прав на создание."
        ),
    }

    response = requests.post(url, headers=HEADERS, json=payload)
    return response.status_code, safe_json(response)


def save_report(report: Dict[str, Any], output_file: str) -> None:
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Проверка создания задач в очереди Tracker")
    parser.add_argument("--queue", default="SVT", help="Ключ очереди (по умолчанию SVT)")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Только проверить доступ к очереди без создания задачи",
    )
    parser.add_argument(
        "--output",
        default="tracker_issue_creation_check.json",
        help="Файл для сохранения отчёта",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    queue_key = args.queue.upper()

    print(f"🚀 Проверка создания задач в очереди {queue_key}")
    report: Dict[str, Any] = {
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "queue": queue_key,
        "queue_check": {},
        "issue_create": {},
    }

    queue_status, queue_data = check_queue(queue_key)
    report["queue_check"] = {
        "status_code": queue_status,
        "ok": queue_status == 200,
        "response": queue_data,
    }

    if queue_status == 200:
        print(f"✅ Очередь {queue_key} доступна")
    else:
        print(f"❌ Очередь {queue_key} недоступна, HTTP {queue_status}")
        print("Подробности:", json.dumps(queue_data, ensure_ascii=False)[:400])
        save_report(report, args.output)
        print(f"💾 Отчёт сохранён в {args.output}")
        return

    if args.check_only:
        print("ℹ️ Режим check-only: создание задачи пропущено")
        save_report(report, args.output)
        print(f"💾 Отчёт сохранён в {args.output}")
        return

    create_status, create_data = create_test_issue(queue_key)
    issue_key = create_data.get("key") if isinstance(create_data, dict) else None
    issue_self = create_data.get("self") if isinstance(create_data, dict) else None
    success = create_status in (200, 201) and issue_key is not None

    report["issue_create"] = {
        "status_code": create_status,
        "ok": success,
        "issue_key": issue_key,
        "issue_self": issue_self,
        "response": create_data,
    }

    if success:
        print(f"✅ Тестовая задача создана: {issue_key}")
        if issue_self:
            print(f"🔗 {issue_self}")
    else:
        print(f"❌ Не удалось создать задачу, HTTP {create_status}")
        print("Подробности:", json.dumps(create_data, ensure_ascii=False)[:500])

    save_report(report, args.output)
    print(f"💾 Отчёт сохранён в {args.output}")


if __name__ == "__main__":
    main()
