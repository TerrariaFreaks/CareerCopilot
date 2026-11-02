from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from google.genai import errors
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent import run_agent
from app.database import get_db
from app.deps import get_current_user
from app.limits import check_run_limit
from app.llm import QuotaExceeded
from app.models import AgentRun, Application, User

router = APIRouter(prefix="/api/applications", tags=["applications"])

Status = Literal["saved", "applied", "interview", "offer", "rejected"]


class ApplicationCreate(BaseModel):
    company: str = Field(default="", max_length=200)
    job_title: str = Field(default="", max_length=200)
    job_text: str = Field(min_length=50, max_length=20000)


class ApplicationUpdate(BaseModel):
    company: Optional[str] = Field(default=None, max_length=200)
    job_title: Optional[str] = Field(default=None, max_length=200)
    status: Optional[Status] = None


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


def _get_owned(db: Session, user: User, application_id: int) -> Application:
    application = db.get(Application, application_id)
    # 404 (not 403) for other people's rows, so we don't reveal that the id exists.
    if application is None or application.user_id != user.id:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.post("", response_model=ApplicationDetail, status_code=201)
def create_application(
    body: ApplicationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile_text = user.profile.content if user.profile else ""
    if len(profile_text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Save your profile first (PUT /api/profile).")

    check_run_limit(db, user.id)

    # Record the run first so parallel requests can't sneak past the limit.
    run = AgentRun(user_id=user.id)
    db.add(run)
    db.commit()

    try:
        events = list(run_agent(profile_text, body.job_text))
    except Exception as e:
        # A failed run shouldn't use up the user's daily allowance.
        db.delete(run)
        db.commit()
        if isinstance(e, QuotaExceeded):
            raise HTTPException(status_code=429, detail=str(e)) from e
        if isinstance(e, errors.APIError):
            raise HTTPException(status_code=502, detail=f"Gemini API error ({e.code}). Try again shortly.") from e
        if isinstance(e, RuntimeError):
            raise HTTPException(status_code=500, detail=str(e)) from e
        raise

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
    return _get_owned(db, user, application_id)


@router.patch("/{application_id}", response_model=ApplicationDetail)
def update_application(
    application_id: int,
    body: ApplicationUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    application = _get_owned(db, user, application_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(application, field, value.strip() if isinstance(value, str) else value)
    db.commit()
    db.refresh(application)
    return application


@router.delete("/{application_id}", status_code=204)
def delete_application(
    application_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    application = _get_owned(db, user, application_id)
    db.delete(application)
    db.commit()