import os
from dotenv import load_dotenv

load_dotenv()

TRACKER_TOKEN = os.getenv("TRACKER_TOKEN")
TRACKER_ORG_ID = os.getenv("TRACKER_ORG_ID")
TRACKER_CLOUD_ORG_ID = os.getenv("TRACKER_CLOUD_ORG_ID")
DEFAULT_PROJECT_KEY = os.getenv("DEFAULT_PROJECT_KEY", "SO")
DEFAULT_TASKS_LIMIT = int(os.getenv("DEFAULT_TASKS_LIMIT", "15"))

LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
LM_TEMPERATURE = float(os.getenv("LM_TEMPERATURE", "0.4"))
LM_MAX_TOKENS = int(os.getenv("LM_MAX_TOKENS", "2000"))