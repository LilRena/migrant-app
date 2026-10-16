from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.steps import StepTemplate, StudentStep, StepStatus, DeadlineType
from app.models.profile import StudentProfile


def calculate_due_date(template: StepTemplate, profile: StudentProfile) -> date | None:
    """Return the due date for a step given the student's profile dates."""
    if template.deadline_type == DeadlineType.days_after_arrival:
        if profile.arrival_date is None or template.deadline_days is None:
            return None
        return profile.arrival_date + timedelta(days=template.deadline_days)
    if template.deadline_type == DeadlineType.days_before_visa_expiry:
        if profile.visa_expiry is None or template.deadline_days is None:
            return None
        return profile.visa_expiry - timedelta(days=template.deadline_days)
    return None  # deadline_type == "none"


def assign_steps(db: Session, student_id: int, profile: StudentProfile) -> None:
    """
    Create StudentStep rows for all templates that match the student's country
    (or templates for all countries, i.e. country_code IS NULL).
    Skips templates that already have a row for this student — no duplicates.
    Does NOT commit; the caller is responsible for db.commit().
    """
    templates = (
        db.query(StepTemplate)
        .filter(
            or_(
                StepTemplate.country_code == profile.country_code,
                StepTemplate.country_code.is_(None),
            )
        )
        .order_by(StepTemplate.order)
        .all()
    )

    existing_template_ids = {
        row.template_id
        for row in db.query(StudentStep.template_id).filter(
            StudentStep.student_id == student_id
        )
    }

    for template in templates:
        if template.id in existing_template_ids:
            continue
        db.add(StudentStep(
            student_id=student_id,
            template_id=template.id,
            due_date=calculate_due_date(template, profile),
        ))


def recalculate_due_dates(db: Session, student_id: int, profile: StudentProfile) -> None:
    """
    Update due_date for all non-approved steps when the student changes dates.
    Approved steps are not touched — the deadline has already passed its purpose.
    Does NOT commit; the caller is responsible for db.commit().
    """
    steps = (
        db.query(StudentStep)
        .join(StepTemplate, StudentStep.template_id == StepTemplate.id)
        .filter(
            StudentStep.student_id == student_id,
            StudentStep.status != StepStatus.approved,
        )
        .all()
    )

    for step in steps:
        template = db.get(StepTemplate, step.template_id)
        step.due_date = calculate_due_date(template, profile)
