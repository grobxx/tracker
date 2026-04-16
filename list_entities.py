#!/usr/bin/env python3
"""
Быстрая выгрузка проектов, портфелей и целей из Яндекс Трекера.
Без очередей и задач.
"""

import os
import json
from dotenv import load_dotenv
from yandex_tracker_client import TrackerClient

# Загружаем настройки из .env
load_dotenv()

TRACKER_TOKEN = os.getenv("TRACKER_TOKEN")
ORG_ID = os.getenv("TRACKER_ORG_ID")

# Типы сущностей, которые хотим выгрузить
# API Entities (Сущности) предоставляет унифицированный набор методов для управления целями, проектами или портфелями проектов[reference:0].
ENTITY_TYPES = ["project", "portfolio", "goal"]


def fetch_entities(client, entity_type):
    """
    Получает список сущностей указанного типа (проект, портфель или цель).
    Использует метод поиска сущностей API[reference:1].
    """
    print(f"  Загружаю {entity_type}...")
    try:
        # Используем метод поиска entities
        entities = list(client.entities.find(entity_type))
        print(f"    Найдено: {len(entities)}")
        return entities
    except Exception as e:
        print(f"    Ошибка при загрузке {entity_type}: {e}")
        return []


def format_entity(entity, entity_type):
    """Извлекает из сущности только самые нужные поля для отчета."""
    # Поля summary, description, lead, participants, customers, status определены в документации API[reference:2]
    lead_display = None
    if hasattr(entity, 'lead') and entity.lead:
        lead_display = entity.lead.display

    # Получаем статус сущности[reference:3]
    status = getattr(entity, 'entityStatus', None) or getattr(entity, 'status', None)

    return {
        "id": getattr(entity, 'id', None),
        "short_id": getattr(entity, 'shortId', None),
        "key": getattr(entity, 'key', None),
        "name": getattr(entity, 'summary', None),
        "description": getattr(entity, 'description', None),
        "status": status,
        "lead": lead_display,
        "start_date": getattr(entity, 'start', None),
        "end_date": getattr(entity, 'end', None),
    }


def main():
    print("🚀 Загружаю проекты, портфели и цели из Яндекс Трекера...")

    # Подключаемся к API
    try:
        client = TrackerClient(token=TRACKER_TOKEN, org_id=ORG_ID)
        current_user = client.myself
        print(f"✅ Подключение успешно. Пользователь: {current_user.display}")
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return

    # Собираем все сущности в один словарь
    all_data = {}

    for entity_type in ENTITY_TYPES:
        entities = fetch_entities(client, entity_type)
        all_data[entity_type] = [format_entity(e, entity_type) for e in entities]

    # Сохраняем результат в файл
    output_file = "entities_list.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n💾 Результат сохранен в {output_file}")

    # Краткая сводка в консоли
    print("\n📊 Сводка:")
    for entity_type, entities in all_data.items():
        print(f"  {entity_type}: {len(entities)} шт.")
        if entities:
            # Показываем несколько примеров
            for i, entity in enumerate(entities[:3], 1):
                name = entity.get('name', 'Без названия')
                status = entity.get('status', 'статус не указан')
                print(f"    {i}. {name} (ID: {entity.get('id')}, статус: {status})")
            if len(entities) > 3:
                print(f"    ... и еще {len(entities)-3}")

    print("\n✨ Готово!")


if __name__ == "__main__":
    main()