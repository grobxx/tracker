#!/usr/bin/env python3
"""
Выгрузка целей (goals) из Яндекс Трекера с фильтром по тегу.
"""

import os
import json
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

def fetch_goals_by_tag(tag="DevGoal_2026"):
    url = f"{BASE_URL}/v3/entities/goal/_search"
    payload = {
        "filter": {
            "tags": {
                "$in": [tag]
            }
        }
    }
    print(f"🔍 Ищем цели с тегом '{tag}'...")
    response = requests.post(url, headers=HEADERS, json=payload)
    print(f"Статус ответа: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ Ошибка: {response.text}")
        return []
    
    # Пытаемся распарсить JSON
    try:
        data = response.json()
        print(f"Тип полученных данных: {type(data)}")
        # Если data — список, возвращаем его
        if isinstance(data, list):
            return data
        # Если data — словарь с ключом 'items' или 'goals'
        elif isinstance(data, dict):
            if 'items' in data:
                return data['items']
            elif 'goals' in data:
                return data['goals']
            else:
                # Может быть, сам словарь — это одна цель?
                # Но мы ожидаем список, поэтому лучше вернуть пустой список
                print("Получен словарь, но не содержит 'items' или 'goals'. Содержимое:")
                print(json.dumps(data, ensure_ascii=False, indent=2)[:500])
                return []
        else:
            print("Неожиданный тип данных:", type(data))
            return []
    except json.JSONDecodeError as e:
        print(f"Ошибка парсинга JSON: {e}")
        print("Ответ сервера (первые 500 символов):", response.text[:500])
        return []

def save_goals(goals, filename="goals_devgoal_2026.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(goals, f, ensure_ascii=False, indent=2, default=str)
    print(f"💾 Сохранено в {filename}")

def print_summary(goals):
    print("\n📊 Сводка по целям:")
    for g in goals:
        # Если g — строка, пропускаем или выводим её
        if isinstance(g, str):
            print(f"  (строка): {g[:100]}")
            continue
        short_id = g.get("shortId", "?")
        summary = g.get("summary", "Без названия")
        status = g.get("entityStatus", "?")
        progress = g.get("progressPercentage", 0)
        print(f"  {short_id} — {summary} (статус: {status}, прогресс: {progress*100:.0f}%)")

def main():
    print("🚀 Выгрузка целей с тегом DevGoal_2026\n")
    goals = fetch_goals_by_tag("DevGoal_2026")
    if not goals:
        print("Цели не найдены или произошла ошибка.")
        # Сохраним пустой результат, чтобы не ломать вывод
        save_goals([], "goals_devgoal_2026.json")
        return
    
    save_goals(goals)
    print_summary(goals)
    
    # Упрощённая версия
    simplified = []
    for g in goals:
        if isinstance(g, dict):
            simplified.append({
                "shortId": g.get("shortId"),
                "summary": g.get("summary"),
                "status": g.get("entityStatus"),
                "progress": g.get("progressPercentage"),
                "description": g.get("description"),
                "tags": g.get("tags", []),
                "keyResultItems": g.get("keyResultItems", [])
            })
        else:
            simplified.append({"raw": g})
    with open("goals_devgoal_2026_simple.json", "w", encoding="utf-8") as f:
        json.dump(simplified, f, ensure_ascii=False, indent=2)
    print("💾 Упрощённая версия сохранена в goals_devgoal_2026_simple.json")

if __name__ == "__main__":
    main()