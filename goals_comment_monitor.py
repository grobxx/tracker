#!/usr/bin/env python3
"""
Мониторинг целей: последний комментарий, ответственный, статус + анализ шаблона через LM Studio.
"""

import os
import re
import json
import argparse
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

from lm_client import ask_lm_studio

load_dotenv()
TOKEN = os.getenv("TRACKER_TOKEN")
ORG_ID = os.getenv("TRACKER_ORG_ID")
BASE_URL = "https://api.tracker.yandex.net"

if not TOKEN or not ORG_ID:
    print("❌ Ошибка: TRACKER_TOKEN или TRACKER_ORG_ID не найдены в .env")
    raise SystemExit(1)

HEADERS = {
    "Authorization": f"OAuth {TOKEN}",
    "X-Org-ID": ORG_ID,
    "Content-Type": "application/json",
}

DEFAULT_SHORT_IDS = [
    3748, 3749, 3750, 3814, 3815, 3817, 3818, 3820,
    3824, 3829, 3838, 3845, 3745, 3767, 3768, 3747,
]

SECTION_RESULT = "Результат за отчетный период:"
SECTION_PLANS = "Ближайшие планы:"
SECTION_RISKS = "Описание причин отклонения сроков и предложений по митигации рисков, если применимо:"


def safe_json(response: requests.Response) -> Any:
    try:
        return response.json()
    except Exception:
        return {"raw": response.text[:2000]}


def parse_date(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    return None


def extract_items(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ("values", "items", "goals"):
            value = data.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    return []


def fetch_goal_by_short_id(short_id: int) -> Optional[Dict[str, Any]]:
    url = f"{BASE_URL}/v3/entities/goal/_search"
    payload = {"filter": {"shortId": short_id}}
    response = requests.post(url, headers=HEADERS, json=payload)
    if response.status_code != 200:
        return None
    items = extract_items(safe_json(response))
    if not items:
        return None
    return items[0]


def fetch_goal_detail(goal_id: str, short_id: int) -> Dict[str, Any]:
    # Сначала пробуем v3
    v3_url = f"{BASE_URL}/v3/entities/goal/{goal_id}?expand=all"
    response = requests.get(v3_url, headers=HEADERS)
    if response.status_code == 200 and isinstance(safe_json(response), dict):
        detail = safe_json(response)
    else:
        detail = {}

    # Если в v3 мало полей, добираем v2
    v2_url = f"{BASE_URL}/v2/goals/{short_id}"
    response_v2 = requests.get(v2_url, headers=HEADERS)
    if response_v2.status_code == 200 and isinstance(safe_json(response_v2), dict):
        detail_v2 = safe_json(response_v2)
        detail.update(detail_v2)
    return detail


def fetch_goal_comments(goal_id: str) -> List[Dict[str, Any]]:
    url = f"{BASE_URL}/v3/entities/goal/{goal_id}/comments?expand=all"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        return []
    data = safe_json(response)
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    return []


def get_latest_comment(comments: List[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], Optional[datetime]]:
    best_comment = None
    best_dt = None
    for c in comments:
        dt = parse_date(c.get("updatedAt")) or parse_date(c.get("createdAt"))
        if dt is None:
            continue
        if best_dt is None or dt > best_dt:
            best_dt = dt
            best_comment = c
    return best_comment, best_dt


def extract_status(goal: Dict[str, Any]) -> str:
    raw = goal.get("entityStatus") or goal.get("status")
    if isinstance(raw, dict):
        for key in ("display", "name", "key", "id"):
            value = raw.get(key)
            if value:
                return str(value)
    if raw:
        return str(raw)
    return "Не указан"


def extract_responsible(goal: Dict[str, Any]) -> str:
    for field in ("responsible", "owner", "lead", "assignee", "updatedBy", "createdBy"):
        value = goal.get(field)
        if isinstance(value, dict):
            display = value.get("display") or value.get("name") or value.get("id")
            if display:
                return str(display)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "Не указан"


def has_section(text: str, section_name: str) -> bool:
    if not text:
        return False
    return section_name.lower() in text.lower()


def extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    text = text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(1))
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return None
    return None


def analyze_comment_with_lm(comment_text: str) -> Dict[str, Any]:
    if not comment_text.strip():
        return {
            "quality": "нет комментария",
            "summary": "Комментарий отсутствует.",
            "risks": [],
            "missing_sections": [SECTION_RESULT, SECTION_PLANS, SECTION_RISKS],
        }

    prompt = f"""Проанализируй комментарий по цели.
Нужно проверить наличие разделов:
1) "{SECTION_RESULT}"
2) "{SECTION_PLANS}"
3) "{SECTION_RISKS}"

Верни только JSON:
{{
  "quality": "высокое|среднее|низкое",
  "summary": "краткий вывод в 1-2 предложениях",
  "risks": ["..."],
  "missing_sections": ["..."]
}}

Комментарий:
{comment_text[:12000]}
"""
    raw = ask_lm_studio(
        prompt,
        system_prompt="Ты PM-аналитик. Отвечай строго валидным JSON, без markdown и пояснений.",
    )
    if not raw:
        return {
            "quality": "unknown",
            "summary": "LM Studio не вернула ответ.",
            "risks": [],
            "missing_sections": [],
        }
    parsed = extract_json_object(raw)
    if isinstance(parsed, dict):
        return parsed
    return {
        "quality": "unknown",
        "summary": f"Не удалось распарсить JSON от LM Studio: {raw[:300]}",
        "risks": [],
        "missing_sections": [],
    }


def build_markdown(records: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    lines.append("# Мониторинг комментариев по целям")
    lines.append("")
    lines.append(f"*Сформировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    lines.append("")
    lines.append("## Сводная таблица")
    lines.append("")
    lines.append("| shortId | Статус | Ответственный | Дата последнего комментария | Шаблон (3/3) |")
    lines.append("|---|---|---|---|---|")

    for r in records:
        ok_sections = [
            r["template_presence"]["result_section"],
            r["template_presence"]["plans_section"],
            r["template_presence"]["risks_section"],
        ]
        score = f"{sum(1 for x in ok_sections if x)}/3"
        lines.append(
            f"| {r['shortId']} | {r['status']} | {r['responsible']} | {r['last_comment_date']} | {score} |"
        )

    lines.append("")
    lines.append("## Детали по целям")
    lines.append("")
    for r in records:
        lines.append(f"### Goal {r['shortId']}: {r['summary']}")
        lines.append(f"- Статус: {r['status']}")
        lines.append(f"- Ответственный: {r['responsible']}")
        lines.append(f"- Последний комментарий: {r['last_comment_date']}")
        lines.append(f"- Наличие блока '{SECTION_RESULT}': {'Да' if r['template_presence']['result_section'] else 'Нет'}")
        lines.append(f"- Наличие блока '{SECTION_PLANS}': {'Да' if r['template_presence']['plans_section'] else 'Нет'}")
        lines.append(f"- Наличие блока '{SECTION_RISKS}': {'Да' if r['template_presence']['risks_section'] else 'Нет'}")
        lm = r.get("lm_analysis", {})
        lines.append(f"- LM оценка: {lm.get('quality', 'unknown')}")
        lines.append(f"- LM вывод: {lm.get('summary', 'Нет данных')}")
        risks = lm.get("risks", [])
        if isinstance(risks, list) and risks:
            lines.append(f"- LM риски: {', '.join(str(x) for x in risks)}")
        missing = lm.get("missing_sections", [])
        if isinstance(missing, list) and missing:
            lines.append(f"- LM отсутствующие разделы: {', '.join(str(x) for x in missing)}")
        lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Мониторинг комментариев по целям с анализом через LM Studio")
    parser.add_argument(
        "--short-ids",
        default=",".join(str(x) for x in DEFAULT_SHORT_IDS),
        help="Список shortId через запятую",
    )
    parser.add_argument("--json-output", default="goals_comments_monitor.json", help="JSON-отчёт")
    parser.add_argument("--md-output", default="goals_comments_monitor.md", help="Markdown-отчёт")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    short_ids = [int(x.strip()) for x in args.short_ids.split(",") if x.strip()]

    print("🚀 Сбор данных по целям...")
    records: List[Dict[str, Any]] = []

    for idx, short_id in enumerate(short_ids, start=1):
        print(f"\n[{idx}/{len(short_ids)}] Обрабатываю goal {short_id}...")
        base_goal = fetch_goal_by_short_id(short_id)
        if not base_goal:
            print("  ❌ Цель не найдена или нет доступа")
            records.append({
                "shortId": short_id,
                "summary": "Не найдена",
                "status": "Не найден",
                "responsible": "Не указан",
                "last_comment_date": "Нет данных",
                "last_comment_text": "",
                "template_presence": {
                    "result_section": False,
                    "plans_section": False,
                    "risks_section": False,
                },
                "lm_analysis": {
                    "quality": "unknown",
                    "summary": "Цель не найдена.",
                    "risks": [],
                    "missing_sections": [SECTION_RESULT, SECTION_PLANS, SECTION_RISKS],
                },
            })
            continue

        goal_id = str(base_goal.get("id"))
        detail = fetch_goal_detail(goal_id, short_id)
        goal = dict(base_goal)
        goal.update(detail)

        comments = fetch_goal_comments(goal_id)
        last_comment, last_comment_dt = get_latest_comment(comments)
        last_comment_text = (last_comment.get("text") if isinstance(last_comment, dict) else "") or ""
        last_comment_date = (
            last_comment_dt.strftime("%Y-%m-%d %H:%M:%S %z")
            if last_comment_dt else "Нет данных"
        )

        presence = {
            "result_section": has_section(last_comment_text, SECTION_RESULT),
            "plans_section": has_section(last_comment_text, SECTION_PLANS),
            "risks_section": has_section(last_comment_text, SECTION_RISKS),
        }

        print(f"  💬 Последний комментарий: {last_comment_date}")
        print(f"  🤖 Анализ через LM Studio...")
        lm_analysis = analyze_comment_with_lm(last_comment_text)

        records.append({
            "shortId": short_id,
            "id": goal_id,
            "summary": goal.get("summary") or goal.get("name") or "Без названия",
            "status": extract_status(goal),
            "responsible": extract_responsible(goal),
            "last_comment_date": last_comment_date,
            "last_comment_text": last_comment_text,
            "template_presence": presence,
            "lm_analysis": lm_analysis,
        })

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "goals_count": len(records),
        "records": records,
        "required_template_sections": [SECTION_RESULT, SECTION_PLANS, SECTION_RISKS],
    }

    with open(args.json_output, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n💾 JSON сохранён: {args.json_output}")

    md = build_markdown(records)
    with open(args.md_output, "w", encoding="utf-8") as f:
        f.write(md + "\n")
    print(f"💾 MD сохранён: {args.md_output}")
    print("✅ Готово")


if __name__ == "__main__":
    main()
