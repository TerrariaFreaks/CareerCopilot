import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AgentRun

RUNS_PER_DAY = int(os.getenv("RUNS_PER_USER_PER_DAY", "5"))
PACIFIC = ZoneInfo("America/Los_Angeles")


def _today_start_utc() -> datetime:
    """Midnight Pacific today, expressed in UTC (matches Gemini's quota reset)."""
    now_pacific = datetime.now(PACIFIC)
    start_pacific = now_pacific.replace(hour=0, minute=0, second=0, microsecond=0)
    return start_pacific.astimezone(timezone.utc)


def runs_today(db: Session, user_id: int) -> int:
    stmt = select(func.count(AgentRun.id)).where(
        AgentRun.user_id == user_id, AgentRun.created_at >= _today_start_utc()
    )
    return db.scalar(stmt) or 0


def check_run_limit(db: Session, user_id: int) -> None:
    if runs_today(db, user_id) >= RUNS_PER_DAY:
        raise HTTPException(
            status_code=429,
            detail=f"Daily limit of {RUNS_PER_DAY} resume runs reached. Resets at midnight Pacific time.",
        )