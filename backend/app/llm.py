import os
import random
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
DAILY_LIMIT = int(os.getenv("DAILY_CALL_LIMIT", "100"))

# Gemini's daily quota resets at midnight Pacific time, so we count days the same way.
PACIFIC = ZoneInfo("America/Los_Angeles")
_usage = {"day": None, "count": 0}
_client = None


class QuotaExceeded(Exception):
    """Raised when our own daily safety cap is reached."""


def _get_client():
    global _client
    if _client is None:
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not set. Check your .env file.")
        _client = genai.Client(api_key=key)
    return _client


def _count_call():
    today = datetime.now(PACIFIC).date().isoformat()
    if _usage["day"] != today:
        _usage["day"] = today
        _usage["count"] = 0
    if _usage["count"] >= DAILY_LIMIT:
        raise QuotaExceeded(f"Daily cap of {DAILY_LIMIT} calls reached. Resets at midnight Pacific time.")
    _usage["count"] += 1


def usage():
    today = datetime.now(PACIFIC).date().isoformat()
    used = _usage["count"] if _usage["day"] == today else 0
    return {"day_pacific": today, "calls_used": used, "daily_cap": DAILY_LIMIT, "model": MODEL}


def ask(system, user, json_mode=False, max_retries=5):
    _count_call()
    config = types.GenerateContentConfig(
        system_instruction=system,
        temperature=0.4,
        response_mime_type="application/json" if json_mode else "text/plain",
    )
    for attempt in range(max_retries):
        try:
            response = _get_client().models.generate_content(
                model=MODEL, contents=user, config=config
            )
            return response.text or ""
        except errors.APIError as e:
            retryable = e.code in (429, 500, 503)
            if not retryable or attempt == max_retries - 1:
                raise
            time.sleep(min(2 ** attempt + random.random(), 30))
    return ""