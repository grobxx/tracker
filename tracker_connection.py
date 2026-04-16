import os
from typing import Optional

from dotenv import load_dotenv
from yandex_tracker_client import TrackerClient

load_dotenv()


def _resolve_org_params() -> dict:
    token = os.getenv("TRACKER_TOKEN")
    org_id = os.getenv("TRACKER_ORG_ID")
    cloud_org_id = os.getenv("TRACKER_CLOUD_ORG_ID")

    if not token:
        raise RuntimeError("Не найден TRACKER_TOKEN в .env")

    if org_id:
        return {"token": token, "org_id": org_id}
    if cloud_org_id:
        return {"token": token, "cloud_org_id": cloud_org_id}

    raise RuntimeError("Укажите TRACKER_ORG_ID или TRACKER_CLOUD_ORG_ID в .env")


def get_tracker_client() -> TrackerClient:
    """
    Инициализация клиента по официальной схеме:
    - org_id для Яндекс 360
    - cloud_org_id для Yandex Cloud
    """
    return TrackerClient(**_resolve_org_params())


def get_auth_mode() -> Optional[str]:
    if os.getenv("TRACKER_ORG_ID"):
        return "org_id"
    if os.getenv("TRACKER_CLOUD_ORG_ID"):
        return "cloud_org_id"
    return None
