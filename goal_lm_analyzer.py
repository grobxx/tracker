#!/usr/bin/env python3
"""
Анализ цели из полной выгрузки через LM Studio.

Что делает:
1) Читает JSON-файл с целями (обычно goals_<tag>.json).
2) Выбирает цель по --short-id (или первую).
3) Определяет последний комментарий по дате.
4) Формирует структурированный markdown-отчёт через LM Studio.
"""

import argparse
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from lm_client import ask_lm_studio


def parse_iso_date(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    # Формат Tracker обычно: 2026-03-13T12:12:48.082+0000
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f%z")
    except ValueError:
        pass
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z")
    except ValueError:
        return None


def load_goals(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]

    if isinstance(data, dict):
        for key in ("values", "items", "goals"):
            items = data.get(key)
            if isinstance(items, list):
                return [x for x in items if isinstance(x, dict)]
        # Если вдруг это одна цель-объект
        if "id" in data and data.get("entityType") == "goal":
            return [data]

    return []


def pick_goal(goals: List[Dict[str, Any]], short_id: Optional[int]) -> Dict[str, Any]:
    if not goals:
        raise ValueError("Список целей пуст.")

    if short_id is None:
        return goals[0]

    for goal in goals:
        if goal.get("shortId") == short_id:
            return goal

    raise ValueError(f"Цель с shortId={short_id} не найдена в файле.")


def get_comment_timestamp(comment: Dict[str, Any]) -> Optional[datetime]:
    return parse_iso_date(comment.get("updatedAt")) or parse_iso_date(comment.get("createdAt"))


def find_last_comment(comments: Any) -> Tuple[Optional[Dict[str, Any]], Optional[datetime]]:
    if not isinstance(comments, list):
        return None, None

    best_comment = None
    best_ts = None
    for item in comments:
        if not isinstance(item, dict):
            continue
        ts = get_comment_timestamp(item)
        if ts is None:
            continue
        if best_ts is None or ts > best_ts:
            best_ts = ts
            best_comment = item
    return best_comment, best_ts


def build_prompt(goal: Dict[str, Any], last_comment: Optional[Dict[str, Any]], last_comment_ts: Optional[datetime]) -> str:
    short_id = goal.get("shortId")
    goal_id = goal.get("id")
    summary = goal.get("summary") or "Без названия"
    status = goal.get("entityStatus") or goal.get("status") or "Не указан"
    progress = goal.get("progressPercentage")
    progress_text = f"{round(progress * 100)}%" if isinstance(progress, (int, float)) else "Не указан"
    tags = goal.get("tags", [])
    description = goal.get("description") or ""
    comments = goal.get("comments", [])

    last_comment_text = "Комментариев нет."
    last_comment_author = "Не указан"
    last_comment_date = "Нет данных"

    if last_comment:
        last_comment_text = (last_comment.get("text") or "").strip() or "Текст комментария пуст."
        created_by = last_comment.get("createdBy", {})
        if isinstance(created_by, dict):
            last_comment_author = created_by.get("display") or "Не указан"
        if last_comment_ts:
            last_comment_date = last_comment_ts.strftime("%Y-%m-%d %H:%M:%S %z")

    prompt = f"""Ты — аналитик проектной деятельности. Подготовь структурированный отчёт по цели в формате Markdown.

Требования к структуре:
1. Краткая карточка цели (ID, shortId, статус, прогресс, теги).
2. Анализ цели: что уже сделано, что вызывает риски, что непонятно из данных.
3. Последний комментарий:
   - дата,
   - автор,
   - краткое содержание (3-5 пунктов),
   - что это значит для статуса цели.
4. Рекомендации: 3-5 конкретных действий.
5. Короткий итог (2-3 предложения).

Пиши на русском, четко и без воды.

ДАННЫЕ ЦЕЛИ:
- goal id: {goal_id}
- shortId: {short_id}
- summary: {summary}
- status: {status}
- progress: {progress_text}
- tags: {tags}
- comments_count: {len(comments) if isinstance(comments, list) else 0}

Описание цели:
{description[:6000] if description else "Описание отсутствует"}

Последний комментарий:
- дата: {last_comment_date}
- автор: {last_comment_author}
- текст:
{last_comment_text[:10000]}
"""
    return prompt


def save_report(report: str, goal: Dict[str, Any], output: Optional[str]) -> str:
    short_id = goal.get("shortId", "unknown")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = output or f"goal_report_{short_id}_{timestamp}.md"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# Анализ цели {short_id}\n\n")
        f.write(f"*Сгенерировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
        f.write(report)
        f.write("\n")
    return filename


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Анализ цели через LM Studio на основе полной выгрузки")
    parser.add_argument("--input", default="goals_devgoal_2026.json", help="Путь к JSON с целями")
    parser.add_argument("--short-id", type=int, help="shortId цели для анализа")
    parser.add_argument("--output", help="Имя выходного markdown-файла")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print("🚀 Анализ цели через LM Studio")

    goals = load_goals(args.input)
    if not goals:
        print(f"❌ В файле {args.input} не найдено целей.")
        return

    try:
        goal = pick_goal(goals, args.short_id)
    except ValueError as e:
        print(f"❌ {e}")
        return

    comments = goal.get("comments", [])
    last_comment, last_comment_ts = find_last_comment(comments)
    if last_comment_ts:
        print(f"💬 Последний комментарий: {last_comment_ts.strftime('%Y-%m-%d %H:%M:%S %z')}")
    else:
        print("💬 Последний комментарий: не найден")

    prompt = build_prompt(goal, last_comment, last_comment_ts)
    with open("last_goal_prompt.txt", "w", encoding="utf-8") as f:
        f.write(prompt)

    print("🤖 Отправляю запрос в LM Studio...")
    report = ask_lm_studio(
        prompt,
        system_prompt="Ты — опытный project analyst. Отвечай структурированно в markdown, строго по входным данным.",
    )
    if not report:
        print("❌ Не удалось получить ответ от LM Studio.")
        return

    path = save_report(report, goal, args.output)
    print(f"✅ Отчёт сохранён: {path}")


if __name__ == "__main__":
    main()
