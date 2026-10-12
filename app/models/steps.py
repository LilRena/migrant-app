from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, ForeignKey, Enum, UniqueConstraint
from app.db import Base
import enum


class DeadlineType(str, enum.Enum):
    days_after_arrival = "days_after_arrival"
    days_before_visa_expiry = "days_before_visa_expiry"
    none = "none"


class StepStatus(str, enum.Enum):
    todo = "todo"
    submitted = "submitted"
    approved = "approved"
    rejected = "rejected"


class StepTemplate(Base):
    __tablename__ = "step_templates"

    id = Column(Integer, primary_key=True)
    country_code = Column(String(10), nullable=True)  # NULL = for all countries
    order = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String)
    location = Column(String)
    deadline_type = Column(Enum(DeadlineType), nullable=False)
    deadline_days = Column(Integer, nullable=True)
    requires_upload = Column(Boolean, default=False, nullable=False)
    is_demo = Column(Boolean, default=True, nullable=False)


class StudentStep(Base):
    __tablename__ = "student_steps"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("step_templates.id"), nullable=False)
    status = Column(Enum(StepStatus), default=StepStatus.todo, nullable=False)
    due_date = Column(Date, nullable=True)
    file_path = Column(String, nullable=True)
    uploaded_at = Column(DateTime, nullable=True)
    staff_comment = Column(String, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("student_id", "template_id", name="uq_student_template"),
    )
