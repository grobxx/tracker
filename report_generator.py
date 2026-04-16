#!/usr/bin/env python3
import json
from datetime import datetime
from tracker_client import get_tasks
from lm_client import ask_lm_studio
import config

def build_prompt(tasks, project_key):
    tasks_json = json.dumps(tasks, ensure_ascii=False, indent=2)
    return f"""
Проанализируй список задач проекта {project_key} и подготовь отчёт в формате Markdown.

## Данные о задачах (JSON):
{tasks_json}

## Структура отчёта:
1. **Общая статистика**: количество задач, распределение по статусам, по исполнителям.
2. **Ключевые проблемы/риски** (максимум 3-5 пунктов).
3. **Рекомендации для команды** (2-3 предложения).
4. **Вывод**.
"""

def save_report(analysis, tasks, project_key):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"reports/report_{project_key}_{timestamp}.md"
    # Создаём папку reports, если её нет
    import os
    os.makedirs("reports", exist_ok=True)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# 📊 Отчёт по проекту {project_key}\n\n")
        f.write(f"**Дата генерации:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## 🤖 Анализ модели\n\n")
        f.write(analysis)
        f.write("\n\n## 📋 Исходные данные (задачи)\n\n")
        f.write("| Ключ | Название | Статус | Исполнитель |\n")
        f.write("|------|----------|--------|-------------|\n")
        for t in tasks:
            summary = t['summary'][:60].replace('|', '\\|')
            f.write(f"| {t['key']} | {summary} | {t['status']} | {t['assignee']} |\n")
    print(f"✅ Отчёт сохранён: {filename}")

def main():
    print("🚀 Запуск генератора отчётов...")
    tasks = get_tasks()
    if not tasks:
        print("Нет задач для анализа.")
        return

    prompt = build_prompt(tasks, config.DEFAULT_PROJECT_KEY)
    print("📤 Отправляю данные в LM Studio...")
    analysis = ask_lm_studio(prompt)
    if not analysis:
        print("Не удалось получить ответ от модели.")
        return

    save_report(analysis, tasks, config.DEFAULT_PROJECT_KEY)
    print("✅ Готово!")

if __name__ == "__main__":
    main()