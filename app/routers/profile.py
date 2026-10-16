from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.profile import StudentProfile
from app.models.user import User
from app.schemas.profile import ProfileRequest, ProfileResponse
from app.security import require_student
from app.services.steps import assign_steps, recalculate_due_dates

router = APIRouter(tags=["profile"])


@router.get("/me/profile", response_model=ProfileResponse)
def get_profile(
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    profile = db.query(StudentProfile).filter(
        StudentProfile.user_id == current_user.id
    ).first()
    if not profile:
        return ProfileResponse()
    return profile


@router.put("/me/profile", response_model=ProfileResponse)
def update_profile(
    body: ProfileRequest,
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    profile = db.query(StudentProfile).filter(
        StudentProfile.user_id == current_user.id
    ).first()

    if not profile:
        profile = StudentProfile(user_id=current_user.id)
        db.add(profile)

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(profile, key, value)

    db.flush()  # make profile.id available without committing

    if profile.country_code and profile.arrival_date:
        assign_steps(db, current_user.id, profile)
        recalculate_due_dates(db, current_user.id, profile)

    db.commit()
    db.refresh(profile)
    return profile
