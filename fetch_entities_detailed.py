#!/usr/bin/env python3
"""
Получение максимально полных данных по проекту, цели или портфелю.
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TRACKER_TOKEN")
ORG_ID = os.getenv("TRACKER_ORG_ID")

if not TOKEN or not ORG_ID:
    print("❌ Ошибка: Не найдены TRACKER_TOKEN или ORG_ID в файле .env")
    exit(1)

HEADERS = {
    "Authorization": f"OAuth {TOKEN}",
    "X-Org-ID": ORG_ID,
    "Content-Type": "application/json"
}
BASE_URL = "https://api.tracker.yandex.net"

def safe_request(url, method="GET", json_data=None, description=""):
    """Выполняет запрос и возвращает результат или None при ошибке."""
    try:
        if method == "GET":
            resp = requests.get(url, headers=HEADERS)
        else:
            resp = requests.post(url, headers=HEADERS, json=json_data or {})
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"  ⚠️ {description} -> статус {resp.status_code}")
            return None
    except Exception as e:
        print(f"  ❌ {description} -> ошибка: {e}")
        return None

def fetch_full_entity(entity_type, entity_id):
    """
    Собирает все возможные данные о сущности (project, portfolio, goal).
    """
    result = {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "data": {}
    }

    # 1. Основная информация через v2 (только для проектов)
    if entity_type == "project":
        print(f"📁 Основные данные (v2)...")
        v2_data = safe_request(f"{BASE_URL}/v2/projects/{entity_id}", description="v2/projects")
        if v2_data:
            result["data"]["v2_basic"] = v2_data

    # 2. Расширенная информация через v3 entities (попробуем без указания полей, чтобы не было 422)
    print(f"🔍 Расширенные данные (v3 entities)...")
    v3_data = safe_request(f"{BASE_URL}/v3/entities/{entity_type}/{entity_id}", description="v3 entities")
    if v3_data:
        result["data"]["v3_entity"] = v3_data

    # 3. Чеклист (только если есть)
    print(f"📋 Чеклист...")
    checklist = safe_request(
        f"{BASE_URL}/v3/entities/{entity_type}/{entity_id}/checklistItems",
        method="POST",
        description="checklist"
    )
    if checklist:
        result["data"]["checklist"] = checklist

    # 4. Очереди (только для проектов)
    if entity_type == "project":
        print(f"📊 Очереди проекта...")
        queues_data = safe_request(f"{BASE_URL}/v2/projects/{entity_id}?expand=queues", description="queues expand")
        if queues_data:
            result["data"]["queues"] = queues_data.get("queues", [])

    # 5. Комментарии (попробуем через v2/comments?entity=...)
    print(f"💬 Комментарии...")
    comments = safe_request(f"{BASE_URL}/v2/comments?entity={entity_type}&entityId={entity_id}", description="comments")
    if comments:
        result["data"]["comments"] = comments

    # 6. Вложения (attachments)
    print(f"📎 Вложения...")
    attachments = safe_request(f"{BASE_URL}/v2/attachments?entity={entity_type}&entityId={entity_id}", description="attachments")
    if attachments:
        result["data"]["attachments"] = attachments

    # 7. История изменений (changelog)
    print(f"🕒 История изменений...")
    changelog = safe_request(f"{BASE_URL}/v2/entities/{entity_type}/{entity_id}/changelog", description="changelog")
    if changelog:
        result["data"]["changelog"] = changelog

    # 8. Связи с другими сущностями (links)
    print(f"🔗 Связи (links)...")
    links = safe_request(f"{BASE_URL}/v2/links?entity={entity_type}&entityId={entity_id}", description="links")
    if links:
        result["data"]["links"] = links

    return result

def main():
    print("🚀 Выгрузка всех данных по сущности...\n")
    
    # Можно передать тип и ID из аргументов командной строки, для простоты зададим вручную
    entity_type = input("Введите тип сущности (project / portfolio / goal): ").strip().lower()
    entity_id = input("Введите ID сущности: ").strip()
    
    if entity_type not in ["project", "portfolio", "goal"]:
        print("❌ Неверный тип. Допустимые: project, portfolio, goal")
        return
    
    full_data = fetch_full_entity(entity_type, entity_id)
    
    # Сохраняем в файл
    filename = f"{entity_type}_{entity_id}_full.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(full_data, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n💾 Полные данные сохранены в {filename}")
    print("✨ Готово!")

if __name__ == "__main__":
    main()