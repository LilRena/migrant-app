from datetime import date
from pydantic import BaseModel
from app.models.steps import DeadlineType, StepStatus


class StepResponse(BaseModel):
    id: int
    template_id: int
    order: int
    title: str
    description: str | None
    location: str | None
    deadline_type: DeadlineType
    deadline_days: int | None
    requires_upload: bool
    is_demo: bool
    status: StepStatus
    due_date: date | None
    staff_comment: str | None


class StepsListResponse(BaseModel):
    done: int
    total: int
    is_demo: bool
    steps: list[StepResponse]
