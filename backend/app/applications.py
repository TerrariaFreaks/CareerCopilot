from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from google.genai import errors
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent import run_agent
from app.database import get_db
from app.deps import get_current_user
from app.llm import QuotaExceeded
from app.models import Application, User

router = APIRouter(prefix="/api/applications", tags=["applications"])


class ApplicationCreate(BaseModel):
    company: str = Field(default="", max_length=200)
    job_title: str = Field(default="", max_length=200)
    job_text: str = Field(min_length=50, max_length=20000)


class ApplicationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company: str
    job_title: str
    status: str
    created_at: datetime


class ApplicationDetail(ApplicationSummary):
    job_text: str
    resume_markdown: Optional[str]
    flags: list


@router.post("", response_model=ApplicationDetail, status_code=201)
def create_application(
    body: ApplicationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile_text = user.profile.content if user.profile else ""
    if len(profile_text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Save your profile first (PUT /api/profile).")

    events = []
    try:
        for event in run_agent(profile_text, body.job_text):
            events.append(event)
    except QuotaExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
    except errors.APIError as e:
        raise HTTPException(status_code=502, detail=f"Gemini API error ({e.code}). Try again shortly.")
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    result = events[-1]
    analysis = next(
        (e.get("data", {}) for e in events if e["step"] == "analyze" and e["status"] == "done"),
        {},
    )
    job_title = body.job_title.strip() or str(analysis.get("role_title", ""))[:200]

    application = Application(
        user_id=user.id,
        company=body.company.strip(),
        job_title=job_title,
        job_text=body.job_text,
        resume_markdown=result["resume"],
        flags=result["flags"],
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.get("", response_model=list[ApplicationSummary])
def list_applications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = (
        select(Application)
        .where(Application.user_id == user.id)
        .order_by(Application.created_at.desc())
    )
    return db.scalars(stmt).all()


@router.get("/{application_id}", response_model=ApplicationDetail)
def get_application(
    application_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    application = db.get(Application, application_id)
    # 404 (not 403) for other people's rows, so we don't reveal that the id exists.
    if application is None or application.user_id != user.id:
        raise HTTPException(status_code=404, detail="Application not found")
    return application