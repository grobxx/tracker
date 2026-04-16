#!/usr/bin/env python3
"""
Агент для анализа проекта Яндекс Трекера с помощью LM Studio.
Загружает проект + комментарии, формирует промпт, вызывает локальную модель.
"""

import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
TOKEN = os.getenv("TRACKER_TOKEN")
ORG_ID = os.getenv("TRACKER_ORG_ID")
LM_URL = "http://localhost:1234/v1"

HEADERS = {"Authorization": f"OAuth {TOKEN}", "X-Org-ID": ORG_ID}
BASE_URL = "https://api.tracker.yandex.net"

def fetch_project_data(project_id):
    """Получает основные данные проекта (v2)."""
    url = f"{BASE_URL}/v2/projects/{project_id}"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code != 200:
        print(f"Ошибка загрузки проекта: {resp.status_code}")
        return None
    return resp.json()

def fetch_project_comments(project_id):
    """Получает все комментарии к проекту (v3)."""
    url = f"{BASE_URL}/v3/entities/project/{project_id}/comments?expand=all"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code != 200:
        print(f"Ошибка загрузки комментариев: {resp.status_code}")
        return []
    return resp.json()

def build_prompt(project, comments):
    """Формирует промпт для модели на основе структурированных данных."""
    # Извлекаем ключевые части из описания (DOD, риски, стейкхолдеры)
    description = project.get("description", "")
    # Обрезаем очень длинное описание, чтобы не перегружать контекст (можно настроить)
    if len(description) > 6000:
        description = description[:6000] + "\n...[описание сокращено]..."
    
    # Формируем список комментариев с датами и текстом
    comments_text = ""
    for c in comments:
        created = c.get("createdAt", "")[:10]
        text = c.get("text", "")
        comments_text += f"\n### Комментарий от {created}\n{text}\n---\n"
    
    prompt = f"""Ты — опытный проект-менеджер и аналитик. Проанализируй проект и подготовь отчёт в формате Markdown.

## Данные проекта

**Название:** {project.get('name')}
**Статус:** {project.get('status')}
**Даты:** {project.get('startDate')} → {project.get('endDate')}
**Руководитель:** {project.get('lead', {}).get('display')}

**Описание (содержит цели, вехи, DOD, риски, стейкхолдеров):**
{description}

## Комментарии (прогресс-отчёты)
{comments_text if comments_text else "Комментариев нет."}

## Задание для анализа
На основе этих данных подготовь отчёт, в котором:

1. **Общая оценка состояния проекта** (статус, отставание от графика, ключевые риски).
2. **Прогресс по вехам** (что выполнено, что отстаёт, какие вехи просрочены).
3. **Основные блокеры и риски** (из описания и комментариев).
4. **Рекомендации** для руководителя проекта и команды (2-3 конкретных действия).
5. **Вывод** (краткое резюме).

Отвечай на русском, чётко, используй пункты и подзаголовки. Не добавляй лишних рассуждений.
"""
    return prompt

def analyze_with_lm(prompt):
    """Отправляет промпт в LM Studio и возвращает ответ."""
    client = OpenAI(base_url=LM_URL, api_key="not-needed")
    try:
        response = client.chat.completions.create(
            model="local-model",
            messages=[
                {"role": "system", "content": "Ты — эксперт по управлению проектами. Отвечай структурированно и только по делу."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=2500
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Ошибка при обращении к LM Studio: {e}")
        return None

def save_report(analysis, project_id):
    """Сохраняет отчёт в Markdown файл."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"report_project_{project_id}_{timestamp}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# Отчёт по проекту {project_id}\n\n")
        f.write(f"*Дата генерации: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
        f.write(analysis)
    print(f"Отчёт сохранён: {filename}")

def main():
    print("🚀 Анализ проекта через LM Studio")
    project_id = input("Введите ID проекта (например, 2465): ").strip()
    if not project_id.isdigit():
        print("ID должен быть числом")
        return
    
    print("Загружаю данные проекта...")
    project = fetch_project_data(project_id)
    if not project:
        return
    
    print("Загружаю комментарии...")
    comments = fetch_project_comments(project_id)
    
    print("Формирую промпт...")
    prompt = build_prompt(project, comments)
    
    # Для отладки можно сохранить промпт в файл
    with open("last_prompt.txt", "w", encoding="utf-8") as f:
        f.write(prompt)
    
    print("Отправляю запрос в LM Studio (убедитесь, что сервер запущен)...")
    analysis = analyze_with_lm(prompt)
    if analysis:
        save_report(analysis, project_id)
        print("✅ Готово!")
    else:
        print("❌ Не удалось получить ответ от модели.")

if __name__ == "__main__":
    main()