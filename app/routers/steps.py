from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.steps import StudentStep, StepTemplate, StepStatus
from app.models.user import User
from app.schemas.steps import StepResponse, StepsListResponse
from app.security import require_student

router = APIRouter(tags=["steps"])


@router.get("/me/steps", response_model=StepsListResponse)
def get_steps(
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(StudentStep, StepTemplate)
        .join(StepTemplate, StudentStep.template_id == StepTemplate.id)
        .filter(StudentStep.student_id == current_user.id)
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
    any_demo = any(s.is_demo for s in steps)

    return StepsListResponse(done=done, total=len(steps), is_demo=any_demo, steps=steps)
