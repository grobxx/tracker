#!/usr/bin/env python3
"""
Чат-агент: текстовый запрос -> структура задачи -> создание в Яндекс Трекере.

Сценарий:
1) Пользователь вводит запрос на создание задачи обычным языком.
2) LM Studio преобразует его в JSON.
3) Скрипт показывает предпросмотр и просит подтверждение.
4) При подтверждении создает задачу в Tracker API.
"""

import os
import re
import json
import argparse
from datetime import datetime
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from yandex_tracker_client.exceptions import NotFound

from lm_client import ask_lm_studio
from tracker_connection import get_auth_mode, get_tracker_client

load_dotenv()

AUTH_MODE = get_auth_mode()

if not AUTH_MODE:
    print("❌ Ошибка: не найден TRACKER_ORG_ID или TRACKER_CLOUD_ORG_ID в .env")
    raise SystemExit(1)


def issue_to_dict(issue: Any) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    for field in ("key", "self", "summary", "description"):
        value = getattr(issue, field, None)
        if value is not None:
            data[field] = value
    return data


def extract_json_block(text: str) -> Optional[Dict[str, Any]]:
    text = text.strip()

    # 1) Полный текст может быть JSON
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # 2) JSON в markdown-блоке
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if fenced:
        try:
            data = json.loads(fenced.group(1))
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    # 3) Попробовать найти объект между первой { и последней }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except Exception:
            return None
    return None


def build_extraction_prompt(user_request: str, default_queue: str) -> str:
    return f"""Преобразуй запрос пользователя в JSON для создания задачи в Яндекс Трекере.
Верни только JSON-объект (без пояснений, без markdown).

Схема:
{{
  "queue": "string, ключ очереди, например SVT",
  "summary": "string, короткий заголовок задачи",
  "description": "string, подробное описание",
  "components": ["string", "..."],
  "tags": ["string", "..."]
}}

Правила:
- Если очередь не указана, поставь "{default_queue}".
- Если компонентов/тегов нет, верни пустые массивы.
- summary должен быть коротким и конкретным.
- description должен включать контекст, ожидаемый результат и критерии приемки.

Запрос пользователя:
{user_request}
"""


def parse_issue_fields_via_lm(user_request: str, default_queue: str) -> Dict[str, Any]:
    prompt = build_extraction_prompt(user_request, default_queue)
    raw = ask_lm_studio(
        prompt,
        system_prompt="Ты извлекаешь структурированные поля для issue tracker. Возвращай только валидный JSON.",
    )
    if not raw:
        raise ValueError("LM Studio не вернула ответ.")

    data = extract_json_block(raw)
    if not data:
        raise ValueError(f"Не удалось распарсить JSON из ответа модели: {raw[:500]}")

    queue = str(data.get("queue") or default_queue).upper().strip()
    summary = str(data.get("summary") or "").strip()
    description = str(data.get("description") or "").strip()
    components = data.get("components") or []
    tags = data.get("tags") or []

    if not isinstance(components, list):
        components = [str(components)]
    if not isinstance(tags, list):
        tags = [str(tags)]

    components = [str(c).strip() for c in components if str(c).strip()]
    tags = [str(t).strip() for t in tags if str(t).strip()]

    if not summary:
        raise ValueError("Модель не заполнила summary.")
    if not description:
        description = "Описание не указано пользователем."

    return {
        "queue": queue,
        "summary": summary,
        "description": description,
        "components": components,
        "tags": tags,
    }


def check_queue(client: Any, queue_key: str) -> bool:
    try:
        client.queues[queue_key]
        return True
    except NotFound:
        return False
    except Exception:
        return False


def create_issue(client: Any, fields: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "queue": fields["queue"],
        "summary": fields["summary"],
        "description": fields["description"],
    }
    if fields.get("components"):
        payload["components"] = fields["components"]
    if fields.get("tags"):
        payload["tags"] = fields["tags"]

    try:
        issue = client.issues.create(**payload)
        return {
            "status_code": 201,
            "ok": True,
            "payload": payload,
            "response": issue_to_dict(issue),
        }
    except Exception as e:
        return {
            "status_code": None,
            "ok": False,
            "payload": payload,
            "response": {"error": str(e)},
        }


def print_preview(fields: Dict[str, Any]) -> None:
    print("\n📝 Предпросмотр задачи:")
    print(f"  queue: {fields['queue']}")
    print(f"  summary: {fields['summary']}")
    print(f"  components: {fields.get('components', [])}")
    print(f"  tags: {fields.get('tags', [])}")
    print("  description:")
    for line in fields["description"].splitlines():
        print(f"    {line}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Создание задач в Tracker по тексту через LM Studio")
    parser.add_argument("--queue", default="SVT", help="Очередь по умолчанию")
    parser.add_argument("--text", help="Текст запроса на создание задачи")
    parser.add_argument("--summary", help="Явный заголовок задачи (перезапишет значение из LM)")
    parser.add_argument("--description", help="Явное описание задачи (перезапишет значение из LM)")
    parser.add_argument("--component", action="append", default=[], help="Компонент (можно указывать несколько раз)")
    parser.add_argument("--tag", action="append", default=[], help="Тег (можно указывать несколько раз)")
    parser.add_argument("--yes", action="store_true", help="Создавать без ручного подтверждения")
    parser.add_argument("--dry-run", action="store_true", help="Только показать распознанные поля")
    parser.add_argument("--output", default="tracker_chat_agent_last_run.json", help="JSON-лог последнего запуска")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    default_queue = args.queue.upper()
    client = get_tracker_client()

    if args.text:
        user_request = args.text.strip()
    else:
        print("💬 Опишите задачу, которую нужно завести в Tracker:")
        user_request = input("> ").strip()

    if not user_request:
        print("❌ Пустой запрос.")
        return

    run_log: Dict[str, Any] = {
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "user_request": user_request,
        "default_queue": default_queue,
        "fields": None,
        "result": None,
    }

    try:
        fields = parse_issue_fields_via_lm(user_request, default_queue)
    except Exception as e:
        print(f"❌ Ошибка разбора запроса моделью: {e}")
        run_log["result"] = {"ok": False, "stage": "extract", "error": str(e)}
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(run_log, f, ensure_ascii=False, indent=2)
        return

    # Явные аргументы командной строки имеют приоритет над распознаванием LM.
    if args.summary:
        fields["summary"] = args.summary.strip()
    if args.description:
        fields["description"] = args.description.strip()
    if args.component:
        fields["components"] = [c.strip() for c in args.component if c.strip()]
    if args.tag:
        fields["tags"] = [t.strip() for t in args.tag if t.strip()]

    run_log["fields"] = fields
    print_preview(fields)

    if not check_queue(client, fields["queue"]):
        print(f"❌ Очередь {fields['queue']} недоступна.")
        run_log["result"] = {"ok": False, "stage": "queue_check", "error": "queue_not_found_or_no_access"}
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(run_log, f, ensure_ascii=False, indent=2)
        return

    if args.dry_run:
        print("\nℹ️ dry-run: задача не создавалась.")
        run_log["result"] = {"ok": True, "stage": "dry_run"}
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(run_log, f, ensure_ascii=False, indent=2)
        print(f"💾 Лог сохранён в {args.output}")
        return

    if not args.yes:
        answer = input("\nСоздать задачу? (yes/no): ").strip().lower()
        if answer not in ("yes", "y", "да", "д"):
            print("⛔ Создание отменено.")
            run_log["result"] = {"ok": False, "stage": "confirm", "error": "cancelled_by_user"}
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(run_log, f, ensure_ascii=False, indent=2)
            print(f"💾 Лог сохранён в {args.output}")
            return

    result = create_issue(client, fields)
    run_log["result"] = result

    if result["ok"]:
        issue = result["response"]
        issue_key = issue.get("key") if isinstance(issue, dict) else None
        issue_self = issue.get("self") if isinstance(issue, dict) else None
        print(f"\n✅ Задача создана: {issue_key or '(ключ не получен)'}")
        if issue_self:
            print(f"🔗 {issue_self}")
    else:
        print(f"\n❌ Не удалось создать задачу. HTTP {result['status_code']}")
        print(f"Подробности: {json.dumps(result['response'], ensure_ascii=False)[:600]}")

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(run_log, f, ensure_ascii=False, indent=2, default=str)
    print(f"💾 Лог сохранён в {args.output}")


if __name__ == "__main__":
    main()
