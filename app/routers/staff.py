from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import get_upload_dir
from app.db import get_db
from app.models.profile import StudentProfile
from app.models.steps import StudentStep, StepStatus, StepTemplate
from app.models.user import User, UserRole
from app.schemas.staff import ReviewRequest, StudentListItem
from app.schemas.steps import StepResponse, StepsListResponse
from app.security import require_staff

router = APIRouter(prefix="/staff", tags=["staff"])


@router.get("/students", response_model=list[StudentListItem])
def list_students(
    has_pending: bool = False,
    has_overdue: bool = False,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    today = date.today()
    students = db.query(User).filter(User.role == UserRole.student).all()
    result = []

    for student in students:
        submitted = (
            db.query(StudentStep)
            .filter(StudentStep.student_id == student.id, StudentStep.status == StepStatus.submitted)
            .count()
        )
        overdue = (
            db.query(StudentStep)
            .filter(
                StudentStep.student_id == student.id,
                StudentStep.due_date < today,
                StudentStep.status != StepStatus.approved,
            )
            .count()
        )

        if has_pending and submitted == 0:
            continue
        if has_overdue and overdue == 0:
            continue

        profile = db.query(StudentProfile).filter(StudentProfile.user_id == student.id).first()
        result.append(StudentListItem(
            id=student.id,
            full_name=student.full_name,
            email=student.email,
            country_code=profile.country_code if profile else None,
            steps_submitted=submitted,
            steps_overdue=overdue,
        ))

    return result


@router.get("/students/{student_id}/steps", response_model=StepsListResponse)
def staff_get_student_steps(
    student_id: int,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    student = db.query(User).filter(User.id == student_id, User.role == UserRole.student).first()
    if not student:
        raise HTTPException(status_code=404, detail="Студент не найден")

    rows = (
        db.query(StudentStep, StepTemplate)
        .join(StepTemplate, StudentStep.template_id == StepTemplate.id)
        .filter(StudentStep.student_id == student_id)
        .order_by(StepTemplate.order)
        .all()
    )

    steps = [
        StepResponse(
            id=ss.id,
            template_id=t.id,
            order=t.order,
            title=t.title,
            description=t.description,
            location=t.location,
            deadline_type=t.deadline_type,
            deadline_days=t.deadline_days,
            requires_upload=t.requires_upload,
            is_demo=t.is_demo,
            status=ss.status,
            due_date=ss.due_date,
            staff_comment=ss.staff_comment,
        )
        for ss, t in rows
    ]

    done = sum(1 for s in steps if s.status == StepStatus.approved)
    return StepsListResponse(
        done=done,
        total=len(steps),
        is_demo=any(s.is_demo for s in steps),
        steps=steps,
    )


@router.get("/steps/{step_id}/file")
def staff_get_file(
    step_id: int,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
    upload_dir: Path = Depends(get_upload_dir),
):
    step = db.query(StudentStep).filter(StudentStep.id == step_id).first()
    if not step or not step.file_path:
        raise HTTPException(status_code=404, detail="Файл не найден")

    full_path = upload_dir / step.file_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Файл не найден")

    return FileResponse(str(full_path))


@router.post("/steps/{step_id}/review")
def review_step(
    step_id: int,
    body: ReviewRequest,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    step = db.query(StudentStep).filter(StudentStep.id == step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="Шаг не найден")

    if step.status != StepStatus.submitted:
        raise HTTPException(status_code=409, detail="Можно проверять только шаги в статусе submitted")

    from datetime import datetime

    if body.decision == "approve":
        step.status = StepStatus.approved
        step.staff_comment = None
    else:
        step.status = StepStatus.rejected
        step.staff_comment = body.comment

    step.reviewed_by = current_user.id
    step.reviewed_at = datetime.utcnow()
    db.commit()

    return {"status": step.status}
