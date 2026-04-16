#!/usr/bin/env python3
"""
Универсальный скрипт для выгрузки полной информации по сущности из Яндекс Трекера.
Поддерживает проекты (project), портфели (portfolio) и цели (goal).
"""

import os
import json
import requests
from dotenv import load_dotenv

# Загружаем токен и ID организации из .env
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

def fetch_all_comments(entity_type, entity_id):
    """Получает все комментарии к сущности."""
    print(f"💬 Загружаю комментарии для {entity_type} {entity_id}...")
    # Используем эндпоинт /v3/entities/<тип_сущности>/<id_сущности>/comments
    # Добавляем параметр expand=all, чтобы получить максимум информации.
    url = f"{BASE_URL}/v3/entities/{entity_type}/{entity_id}/comments?expand=all"
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            comments = response.json()
            print(f"  ✅ Найдено комментариев: {len(comments)}")
            return comments
        else:
            print(f"  ⚠️ Ошибка {response.status_code}: {response.text}")
            return []
    except Exception as e:
        print(f"  ❌ Ошибка при запросе комментариев: {e}")
        return []

def fetch_entity_data(entity_type, entity_id):
    """Получает основные данные о сущности."""
    print(f"📁 Загружаю основные данные {entity_type} {entity_id}...")
    # Для проектов есть отдельный и более богатый эндпоинт v2
    if entity_type == "project":
        url = f"{BASE_URL}/v2/projects/{entity_id}"
    else:
        url = f"{BASE_URL}/v3/entities/{entity_type}/{entity_id}"
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            print(f"  ✅ Основные данные получены")
            return response.json()
        else:
            print(f"  ⚠️ Ошибка {response.status_code}: {response.text}")
            return {}
    except Exception as e:
        print(f"  ❌ Ошибка при запросе основных данных: {e}")
        return {}

def main():
    print("🚀 Универсальная выгрузка данных и комментариев из Яндекс Трекера...\n")
    
    # Запрашиваем у пользователя тип и ID
    entity_type = input("Введите тип сущности (project / portfolio / goal): ").strip().lower()
    entity_id = input("Введите ID сущности (например, '2465'): ").strip()
    
    if entity_type not in ["project", "portfolio", "goal"]:
        print("❌ Неверный тип. Допустимые: project, portfolio, goal")
        return

    # Собираем все данные в один словарь
    full_data = {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "basic_info": fetch_entity_data(entity_type, entity_id),
        "comments": fetch_all_comments(entity_type, entity_id)
    }
    
    # Сохраняем результат в файл
    output_file = f"{entity_type}_{entity_id}_complete.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(full_data, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n💾 Полные данные (включая комментарии) сохранены в файл: {output_file}")
    print("✨ Готово!")

if __name__ == "__main__":
    main()