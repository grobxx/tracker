#!/usr/bin/env python3
"""
Скрипт для исследования структуры Яндекс Трекера.
Выгружает очереди, проекты и примеры задач для анализа.
"""

import json
import os
from datetime import datetime

from dotenv import load_dotenv
from yandex_tracker_client import TrackerClient

# Загружаем настройки из .env файла
load_dotenv()

# --- Конфигурация ---
TRACKER_TOKEN = os.getenv("TRACKER_TOKEN")
ORG_ID = os.getenv("TRACKER_ORG_ID")
OUTPUT_DIR = "tracker_structure"  # Папка, куда сохраним результат


def save_json(data, filename):
    """Сохраняет данные в JSON файл с форматированием."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"  -> Сохранено в {filepath}")


def main():
    print("🚀 Начинаем исследование структуры Яндекс Трекера...")

    # 1. Подключаемся к API
    try:
        client = TrackerClient(token=TRACKER_TOKEN, org_id=ORG_ID)
        # Проверяем подключение, получив информацию о текущем пользователе
        current_user = client.myself
        print(f"✅ Подключение успешно. Пользователь: {current_user.display}")
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        print("Проверьте ваш OAuth-токен и ORG_ID в файле .env")
        return

    structure_report = {
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "user": current_user.display,
            "org_id": ORG_ID,
        },
        "queues": [],
        "projects": [],
        "sample_tasks_by_queue": {},
    }

    # 2. Получаем список всех очередей
    print("\n📋 Получаем список всех очередей...")
    try:
        all_queues = list(client.queues.get_all())
        print(f"  Найдено очередей: {len(all_queues)}")
        for queue in all_queues:
            queue_info = {
                "key": queue.key,
                "name": queue.name,
                "description": getattr(queue, "description", None),
                "lead": getattr(queue.lead, "display", None) if hasattr(queue, "lead") else None,
            }
            structure_report["queues"].append(queue_info)

            # Для каждой очереди получаем несколько примеров задач
            print(f"    -> Получаем примеры задач для очереди '{queue.key}'...")
            try:
                sample_issues = list(client.issues.find(f"Queue: {queue.key}", per_page=5))
                sample_tasks = []
                for issue in sample_issues:
                    task_info = {
                        "key": issue.key,
                        "summary": issue.summary,
                        "status": issue.status.name,
                        "type": issue.type.name if hasattr(issue, "type") else None,
                        "priority": issue.priority.name if hasattr(issue, "priority") else None,
                        "assignee": issue.assignee.display if issue.assignee else None,
                        "created_at": issue.createdAt[:10] if hasattr(issue, "createdAt") else None,
                    }
                    sample_tasks.append(task_info)
                structure_report["sample_tasks_by_queue"][queue.key] = sample_tasks
            except Exception as e:
                print(f"      Ошибка при получении задач для очереди {queue.key}: {e}")
                structure_report["sample_tasks_by_queue"][queue.key] = []

    except Exception as e:
        print(f"  Ошибка при получении списка очередей: {e}")

    # 3. Получаем список всех проектов
    print("\n📁 Получаем список всех проектов...")
    try:
        all_projects = list(client.projects.get_all())
        print(f"  Найдено проектов: {len(all_projects)}")
        for project in all_projects[:50]:  # Ограничим первыми 50 для наглядности
            project_info = {
                "id": project.id,
                "key": project.key,
                "name": project.name,
                "description": getattr(project, "description", None),
                "lead": getattr(project.lead, "display", None) if hasattr(project, "lead") else None,
                "status": getattr(project, "status", None),
            }
            structure_report["projects"].append(project_info)
    except Exception as e:
        print(f"  Ошибка при получении списка проектов: {e}")
        print("  (Возможно, у вас нет прав на просмотр проектов или функция недоступна)")

    # 4. Сохраняем полный отчет
    print(f"\n💾 Сохраняем полную структуру в папку '{OUTPUT_DIR}'...")
    save_json(structure_report, "full_structure.json")

    # 5. Создаем упрощенный файл-шпаргалку с ключами очередей и проектов
    cheat_sheet = {
        "queues_keys": [q["key"] for q in structure_report["queues"]],
        "projects_keys": [p["key"] for p in structure_report["projects"]],
        "sample_tasks_summary": {
            queue: [t["key"] for t in tasks[:3]] for queue, tasks in structure_report["sample_tasks_by_queue"].items()
        },
    }
    save_json(cheat_sheet, "cheat_sheet.json")

    print("\n✨ Исследование завершено!")
    print(
        f"Теперь у вас есть файлы в папке '{OUTPUT_DIR}':\n"
        f"  - full_structure.json: полная информация об очередях, проектах и примерах задач.\n"
        f"  - cheat_sheet.json: краткий справочник с ключами для быстрого доступа.\n"
    )
    print("Используйте эти данные, чтобы понять структуру и правильно настроить фильтры.")


if __name__ == "__main__":
    main()