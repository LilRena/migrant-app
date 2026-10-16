from typing import Literal
from pydantic import BaseModel, model_validator


class ReviewRequest(BaseModel):
    decision: Literal["approve", "reject"]
    comment: str | None = None

    @model_validator(mode="after")
    def comment_required_on_reject(self):
        if self.decision == "reject" and not (self.comment or "").strip():
            raise ValueError("При отказе комментарий обязателен")
        return self


class StudentListItem(BaseModel):
    id: int
    full_name: str
    email: str
    country_code: str | None
    steps_submitted: int
    steps_overdue: int
