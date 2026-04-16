#!/usr/bin/env python3
"""
Выгрузка целей (goals) из Яндекс Трекера с фильтром по тегу.
Использует API v3: POST /v3/entities/goal/_search
"""

import os
import json
import argparse
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TRACKER_TOKEN")
ORG_ID = os.getenv("TRACKER_ORG_ID")

if not TOKEN or not ORG_ID:
    print("❌ Ошибка: TRACKER_TOKEN или ORG_ID не найдены в .env")
    exit(1)

HEADERS = {
    "Authorization": f"OAuth {TOKEN}",
    "X-Org-ID": ORG_ID,
    "Content-Type": "application/json"
}
BASE_URL = "https://api.tracker.yandex.net"

def extract_goal_items(api_response):
    """
    Нормализует ответ API:
    - list -> возвращаем как есть
    - dict с полем values/items -> возвращаем это поле
    """
    if isinstance(api_response, list):
        return api_response
    if isinstance(api_response, dict):
        values = api_response.get("values")
        if isinstance(values, list):
            return values
        items = api_response.get("items")
        if isinstance(items, list):
            return items
    return []

def fetch_goals_by_tag(tag="DevGoal_2026"):
    """
    Ищет цели с указанным тегом.
    Возвращает список целей (каждая цель — словарь).
    """
    url = f"{BASE_URL}/v3/entities/goal/_search"
    
    # Фильтр: тег должен содержать значение (можно искать точное совпадение или in)
    # Поле "tags" в сущности — массив строк. Используем оператор "in".
    payload = {
        "filter": {
            "tags": {
                "$in": [tag]
            }
        }
    }
    
    print(f"🔍 Ищем цели с тегом '{tag}'...")
    response = requests.post(url, headers=HEADERS, json=payload)
    
    if response.status_code != 200:
        print(f"❌ Ошибка {response.status_code}: {response.text}")
        return []
    
    raw_data = response.json()
    goals = extract_goal_items(raw_data)
    total_hits = raw_data.get("hits") if isinstance(raw_data, dict) else None
    if total_hits is not None:
        print(f"✅ Найдено целей: {len(goals)} (всего по запросу: {total_hits})")
    else:
        print(f"✅ Найдено целей: {len(goals)}")
    return goals

def fetch_goal_by_short_id(short_id):
    """Ищет цель по shortId через search API."""
    url = f"{BASE_URL}/v3/entities/goal/_search"
    payload = {
        "filter": {
            "shortId": short_id
        }
    }
    print(f"🔎 Ищем goal по shortId={short_id}...")
    response = requests.post(url, headers=HEADERS, json=payload)
    if response.status_code != 200:
        print(f"❌ Ошибка {response.status_code}: {response.text}")
        return None

    items = extract_goal_items(response.json())
    if not items:
        print("❌ Цель по shortId не найдена.")
        return None
    return items[0]

def fetch_goal_comments(goal_id):
    """Получает комментарии к цели по её ID."""
    url = f"{BASE_URL}/v3/entities/goal/{goal_id}/comments?expand=all"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        print(f"  ⚠️ Не удалось загрузить комментарии для goal {goal_id}: {response.status_code}")
        return []
    data = response.json()
    if isinstance(data, list):
        return data
    return []

def fetch_goal_detail(goal_id):
    """Получает полную карточку цели (включая tags, summary и др.)."""
    url = f"{BASE_URL}/v3/entities/goal/{goal_id}?expand=all"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        print(f"  ⚠️ Не удалось загрузить detail v3 для goal {goal_id}: {response.status_code}")
        return {}
    data = response.json()
    if isinstance(data, dict):
        return data
    return {}

def fetch_goal_detail_v2(short_id):
    """Пробует получить более полные поля цели через v2 по shortId."""
    url = f"{BASE_URL}/v2/goals/{short_id}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        return {}
    data = response.json()
    if isinstance(data, dict):
        return data
    return {}

def extract_tags(goal):
    """Унифицирует теги из разных форматов ответа API."""
    if not isinstance(goal, dict):
        return []
    candidates = [
        goal.get("tags"),
        goal.get("tag"),
        goal.get("labels"),
    ]
    for value in candidates:
        if isinstance(value, list):
            result = []
            for item in value:
                if isinstance(item, str):
                    result.append(item)
                elif isinstance(item, dict):
                    name = item.get("name") or item.get("display") or item.get("key")
                    if name:
                        result.append(str(name))
            if result:
                return result
    return []

def fetch_goal_relations(goal_id):
    """Получает связи цели (relations)."""
    url = f"{BASE_URL}/v3/entities/goal/{goal_id}/relations"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        print(f"  ⚠️ Не удалось загрузить relations для goal {goal_id}: {response.status_code}")
        return []
    data = response.json()
    if isinstance(data, list):
        return data
    return []

def extract_goal_summary(goal):
    """Унифицирует название цели из разных полей API."""
    if not isinstance(goal, dict):
        return "Без названия"
    for key in ("summary", "name", "title"):
        value = goal.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "Без названия"

def enrich_goals(goals, include_comments=True, include_relations=True, include_detail=True):
    """Добавляет в каждую цель дополнительные данные."""
    if not include_comments and not include_relations and not include_detail:
        return goals

    print("\n🔎 Догружаем детали по каждой цели...")
    for idx, goal in enumerate(goals, start=1):
        goal_id = goal.get("id")
        short_id = goal.get("shortId", "?")
        if not goal_id:
            if include_comments:
                goal["comments"] = []
            if include_relations:
                goal["relations"] = []
            print(f"  [{idx}/{len(goals)}] Goal {short_id}: ID отсутствует, детали пропущены")
            continue

        comments_count = 0
        relations_count = 0

        if include_detail:
            detail = fetch_goal_detail(goal_id)
            # Обновляем цель полными полями (tags, summary, status и т.д.), не теряя уже добавленные секции.
            if detail:
                goal.update(detail)
            # У части целей v3 отдаёт только минимальную карточку, поэтому добираем через v2 по shortId.
            if not extract_tags(goal) and short_id not in (None, "?"):
                detail_v2 = fetch_goal_detail_v2(short_id)
                if detail_v2:
                    goal.update(detail_v2)
            goal["tags"] = extract_tags(goal)
            goal["summary"] = extract_goal_summary(goal)

        if include_comments:
            comments = fetch_goal_comments(goal_id)
            goal["comments"] = comments
            comments_count = len(comments)

        if include_relations:
            relations = fetch_goal_relations(goal_id)
            goal["relations"] = relations
            relations_count = len(relations)

        print(
            f"  [{idx}/{len(goals)}] Goal {short_id}: "
            f"комментариев {comments_count}, связей {relations_count}"
        )
    return goals

def save_goals(goals, filename="goals_devgoal_2026.json"):
    """Сохраняет цели в JSON-файл."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(goals, f, ensure_ascii=False, indent=2, default=str)
    print(f"💾 Сохранено в {filename}")

def print_summary(goals):
    """Выводит краткую сводку по целям."""
    print("\n📊 Сводка по целям:")
    for g in goals:
        short_id = g.get("shortId", "?")
        summary = extract_goal_summary(g)
        status = g.get("entityStatus", "?")
        progress = g.get("progressPercentage", 0)
        comments_count = len(g.get("comments", []))
        relations_count = len(g.get("relations", []))
        print(
            f"  {short_id} — {summary} "
            f"(статус: {status}, прогресс: {progress*100:.0f}%, "
            f"комментарии: {comments_count}, связи: {relations_count})"
        )

def parse_args():
    parser = argparse.ArgumentParser(description="Выгрузка goals по тегу")
    parser.add_argument("--tag", default="DevGoal_2026", help="Тег для поиска целей")
    parser.add_argument("--short-id", type=int, help="Проверка и выгрузка одной цели по shortId")
    parser.add_argument(
        "--without-comments",
        action="store_true",
        help="Не выгружать комментарии по целям",
    )
    parser.add_argument(
        "--without-relations",
        action="store_true",
        help="Не выгружать relations по целям",
    )
    return parser.parse_args()

def main():
    args = parse_args()
    tag = args.tag
    include_comments = not args.without_comments
    include_relations = not args.without_relations

    if args.short_id:
        print(f"🚀 Выгрузка цели по shortId {args.short_id}\n")
        goal = fetch_goal_by_short_id(args.short_id)
        if not goal:
            return
        goal_tags = goal.get("tags", [])
        print(f"🏷️ Теги цели {args.short_id}: {goal_tags if goal_tags else 'нет тегов'}")
        goals = [goal]
    else:
        print(f"🚀 Выгрузка целей с тегом {tag}\n")
        goals = fetch_goals_by_tag(tag)
        if not goals:
            print("Цели не найдены.")
            return

    goals = enrich_goals(
        goals,
        include_comments=include_comments,
        include_relations=include_relations,
        include_detail=True,
    )
    normalized_tag = tag.lower().replace(" ", "_")
    save_goals(goals, filename=f"goals_{normalized_tag}.json")
    print_summary(goals)
    
    # Опционально: сохранить в более удобном виде — только ключевые поля
    simplified = []
    for g in goals:
        simplified.append({
            "shortId": g.get("shortId"),
            "summary": extract_goal_summary(g),
            "status": g.get("entityStatus"),
            "progress": g.get("progressPercentage"),
            "description": g.get("description"),
            "tags": g.get("tags", []),
            "keyResultItems": g.get("keyResultItems", []),
            "commentsCount": len(g.get("comments", [])),
            "comments": [c.get("text", "") for c in g.get("comments", []) if isinstance(c, dict)],
            "relationsCount": len(g.get("relations", [])),
            "relations": g.get("relations", []),
        })
    with open(f"goals_{normalized_tag}_simple.json", "w", encoding="utf-8") as f:
        json.dump(simplified, f, ensure_ascii=False, indent=2)
    print(f"💾 Упрощённая версия сохранена в goals_{normalized_tag}_simple.json")

if __name__ == "__main__":
    main()