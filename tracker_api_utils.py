#!/usr/bin/env python3
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

BASE_URL = "https://api.tracker.yandex.net"


def _auth_headers() -> Dict[str, str]:
    load_dotenv()
    token = os.getenv("TRACKER_TOKEN")
    org_id = os.getenv("TRACKER_ORG_ID")
    cloud_org_id = os.getenv("TRACKER_CLOUD_ORG_ID")

    if not token:
        raise RuntimeError("Не найден TRACKER_TOKEN в .env")
    if not org_id and not cloud_org_id:
        raise RuntimeError("Укажите TRACKER_ORG_ID или TRACKER_CLOUD_ORG_ID в .env")

    headers = {
        "Authorization": f"OAuth {token}",
        "Content-Type": "application/json",
    }
    if org_id:
        headers["X-Org-ID"] = org_id
    if cloud_org_id:
        headers["X-Cloud-Org-ID"] = cloud_org_id
    return headers


def safe_json(resp: requests.Response) -> Any:
    try:
        return resp.json()
    except Exception:
        return {"raw": resp.text[:5000]}


def api_call(
    method: str,
    path: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    payload: Optional[Dict[str, Any]] = None,
    timeout: int = 60,
) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    headers = _auth_headers()
    try:
        if method.upper() == "GET":
            resp = requests.get(url, headers=headers, params=params, timeout=timeout)
        else:
            resp = requests.post(url, headers=headers, params=params, json=payload or {}, timeout=timeout)
        return {
            "ok": resp.status_code == 200,
            "status_code": resp.status_code,
            "url": resp.url,
            "data": safe_json(resp),
            "requested_at": datetime.now().isoformat(timespec="seconds"),
        }
    except Exception as e:
        return {
            "ok": False,
            "status_code": None,
            "url": url,
            "data": {"error": str(e)},
            "requested_at": datetime.now().isoformat(timespec="seconds"),
        }


def write_json(path: str, data: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
