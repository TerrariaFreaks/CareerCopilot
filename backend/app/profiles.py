from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Profile, User

router = APIRouter(prefix="/api/profile", tags=["profile"])


class ProfileIn(BaseModel):
    content: str = Field(max_length=30000)


class ProfileOut(BaseModel):
    content: str


@router.get("", response_model=ProfileOut)
def get_profile(user: User = Depends(get_current_user)):
    return ProfileOut(content=user.profile.content if user.profile else "")


@router.put("", response_model=ProfileOut)
def save_profile(
    body: ProfileIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.profile is None:
        user.profile = Profile(content=body.content)
    else:
        user.profile.content = body.content
    db.commit()
    return ProfileOut(content=body.content)