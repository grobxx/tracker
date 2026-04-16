#!/usr/bin/env python3
"""
Скрипт-разведчик по API goals в Яндекс Трекере.

Что делает:
1) Находит цель (по --goal-id или по --tag).
2) Проверяет базовые endpoint'ы для goal.
3) Показывает, какие поля реально приходят в ответах.
4) Сохраняет подробный JSON-отчет.
"""

import os
import json
import argparse
from datetime import datetime
from typing import Any, Dict, List, Tuple

import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TRACKER_TOKEN")
ORG_ID = os.getenv("TRACKER_ORG_ID")

if not TOKEN or not ORG_ID:
    print("❌ Ошибка: TRACKER_TOKEN или TRACKER_ORG_ID не найдены в .env")
    raise SystemExit(1)

BASE_URL = "https://api.tracker.yandex.net"
HEADERS = {
    "Authorization": f"OAuth {TOKEN}",
    "X-Org-ID": ORG_ID,
    "Content-Type": "application/json",
}


def extract_items(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ("values", "items", "goals"):
            value = data.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    return []


def flatten_field_paths(obj: Any, prefix: str = "", depth: int = 0, max_depth: int = 3) -> List[str]:
    if depth > max_depth:
        return []

    paths: List[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            current = f"{prefix}.{key}" if prefix else str(key)
            paths.append(current)
            paths.extend(flatten_field_paths(value, current, depth + 1, max_depth))
    elif isinstance(obj, list) and obj:
        current = f"{prefix}[]"
        paths.append(current)
        first = obj[0]
        paths.extend(flatten_field_paths(first, current, depth + 1, max_depth))
    return paths


def safe_json(resp: requests.Response) -> Any:
    try:
        return resp.json()
    except Exception:
        return {"raw": resp.text[:2000]}


def call_endpoint(method: str, url: str, payload: Dict[str, Any] | None = None) -> Tuple[int, Any]:
    if method == "GET":
        resp = requests.get(url, headers=HEADERS)
    else:
        resp = requests.post(url, headers=HEADERS, json=payload or {})
    return resp.status_code, safe_json(resp)


def choose_goal(goal_id: str | None, tag: str) -> Dict[str, Any] | None:
    if goal_id:
        url = f"{BASE_URL}/v3/entities/goal/{goal_id}"
        code, data = call_endpoint("GET", url)
        if code != 200 or not isinstance(data, dict):
            print(f"❌ Не удалось загрузить goal {goal_id}. Код: {code}")
            return None
        return data

    print(f"🔍 Ищем цели с тегом '{tag}'...")
    url = f"{BASE_URL}/v3/entities/goal/_search"
    payload = {"filter": {"tags": {"$in": [tag]}}}
    code, data = call_endpoint("POST", url, payload)
    if code != 200:
        print(f"❌ Ошибка поиска goals. Код: {code}")
        return None

    items = extract_items(data)
    if not items:
        print("❌ Цели по тегу не найдены.")
        return None

    picked = items[0]
    print(f"✅ Найдено целей: {len(items)}. Беру первую: shortId={picked.get('shortId')}, id={picked.get('id')}")
    return picked


def inspect_goal(goal: Dict[str, Any]) -> Dict[str, Any]:
    goal_id = goal.get("id")
    short_id = goal.get("shortId")

    print(f"\n🧪 Проверяю endpoint'ы для goal id={goal_id}, shortId={short_id}")
    endpoints = [
        {
            "name": "goal_detail",
            "method": "GET",
            "url": f"{BASE_URL}/v3/entities/goal/{goal_id}",
        },
        {
            "name": "goal_comments",
            "method": "GET",
            "url": f"{BASE_URL}/v3/entities/goal/{goal_id}/comments?expand=all",
        },
        {
            "name": "goal_relations",
            "method": "GET",
            "url": f"{BASE_URL}/v3/entities/goal/{goal_id}/relations",
        },
    ]

    result: Dict[str, Any] = {
        "inspected_at": datetime.now().isoformat(timespec="seconds"),
        "goal_id": goal_id,
        "goal_short_id": short_id,
        "goal_summary": goal.get("summary"),
        "endpoints": {},
    }

    for ep in endpoints:
        code, data = call_endpoint(ep["method"], ep["url"])
        key_paths = sorted(set(flatten_field_paths(data)))
        sample_size = len(data) if isinstance(data, list) else (len(data.keys()) if isinstance(data, dict) else 0)
        result["endpoints"][ep["name"]] = {
            "method": ep["method"],
            "url": ep["url"],
            "status_code": code,
            "top_level_type": type(data).__name__,
            "top_level_size": sample_size,
            "field_paths": key_paths[:300],
            "sample": data if isinstance(data, dict) else (data[:2] if isinstance(data, list) else data),
        }
        print(f"  - {ep['name']}: HTTP {code}, type={type(data).__name__}, paths={len(key_paths)}")

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Понять, какие данные доступны по goals из Tracker API")
    parser.add_argument("--goal-id", help="ID цели (если известен)")
    parser.add_argument("--tag", default="DevGoal_2026", help="Тег для поиска цели, если --goal-id не передан")
    parser.add_argument(
        "--output",
        default="goal_api_capabilities.json",
        help="Имя выходного JSON-файла",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print("🚀 Разведка возможностей API для goals")

    goal = choose_goal(args.goal_id, args.tag)
    if not goal:
        return

    report = inspect_goal(goal)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n💾 Отчет сохранен в {args.output}")
    print("✨ Готово")


if __name__ == "__main__":
    main()
