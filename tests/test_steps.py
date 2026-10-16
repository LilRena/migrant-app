"""Tests for Stage 2: profile, step assignment, due-date calculation."""
from datetime import date, timedelta
import pytest

from app.models.steps import StepTemplate, DeadlineType, StudentStep, StepStatus
from app.models.user import User, UserRole
from app.security import hash_password, create_token
from scripts.load_steps import validate_step_data


# ── helpers ──────────────────────────────────────────────────────────────────

def make_student(db, email="s@example.com"):
    user = User(
        email=email,
        hashed_password=hash_password("password1"),
        full_name="Student",
        role=UserRole.student,
    )
    db.add(user)
    db.flush()
    return user


def make_template(db, order, deadline_type, deadline_days=None, country_code=None):
    t = StepTemplate(
        country_code=country_code,
        order=order,
        title=f"Step {order}",
        deadline_type=deadline_type,
        deadline_days=deadline_days,
        requires_upload=True,
        is_demo=True,
    )
    db.add(t)
    db.flush()
    return t


def auth_headers(user):
    return {"Authorization": f"Bearer {create_token({'sub': user.email})}"}


def put_profile(client, headers, **kwargs):
    return client.put("/me/profile", json={k: str(v) for k, v in kwargs.items()}, headers=headers)


# ── profile CRUD ──────────────────────────────────────────────────────────────

def test_get_profile_empty_before_first_put(client, db):
    student = make_student(db, "empty@example.com")
    r = client.get("/me/profile", headers=auth_headers(student))
    assert r.status_code == 200
    assert r.json()["country_code"] is None


def test_put_profile_creates_and_returns(client, db):
    student = make_student(db, "create@example.com")
    r = client.put("/me/profile", json={"country_code": "KZ", "faculty": "IT"}, headers=auth_headers(student))
    assert r.status_code == 200
    assert r.json()["country_code"] == "KZ"
    assert r.json()["faculty"] == "IT"


# ── step assignment ───────────────────────────────────────────────────────────

def test_steps_assigned_when_country_and_arrival_set(client, db):
    student = make_student(db, "assign@example.com")
    make_template(db, 1, DeadlineType.none)
    make_template(db, 2, DeadlineType.none)

    r = client.put("/me/profile", json={
        "country_code": "KZ", "arrival_date": "2026-01-01"
    }, headers=auth_headers(student))
    assert r.status_code == 200

    r2 = client.get("/me/steps", headers=auth_headers(student))
    assert r2.status_code == 200
    data = r2.json()
    assert data["total"] == 2
    assert data["done"] == 0
    assert data["is_demo"] is True


def test_steps_not_assigned_without_arrival_date(client, db):
    student = make_student(db, "noarrival@example.com")
    make_template(db, 1, DeadlineType.none)

    client.put("/me/profile", json={"country_code": "KZ"}, headers=auth_headers(student))
    r = client.get("/me/steps", headers=auth_headers(student))
    assert r.json()["total"] == 0


def test_no_duplicate_steps_on_repeated_put(client, db):
    student = make_student(db, "nodup@example.com")
    make_template(db, 1, DeadlineType.none)

    headers = auth_headers(student)
    client.put("/me/profile", json={"country_code": "KZ", "arrival_date": "2026-01-01"}, headers=headers)
    client.put("/me/profile", json={"country_code": "KZ", "arrival_date": "2026-01-02"}, headers=headers)

    r = client.get("/me/steps", headers=auth_headers(student))
    assert r.json()["total"] == 1  # still 1, not 2


# ── due-date calculation ──────────────────────────────────────────────────────

def test_due_date_none_type(client, db):
    student = make_student(db, "none@example.com")
    make_template(db, 1, DeadlineType.none)

    client.put("/me/profile", json={"country_code": "KZ", "arrival_date": "2026-01-01"}, headers=auth_headers(student))
    steps = client.get("/me/steps", headers=auth_headers(student)).json()["steps"]
    assert steps[0]["due_date"] is None


def test_due_date_days_after_arrival(client, db):
    student = make_student(db, "arrival@example.com")
    make_template(db, 1, DeadlineType.days_after_arrival, deadline_days=7)

    arrival = date(2026, 1, 1)
    client.put("/me/profile", json={"country_code": "KZ", "arrival_date": str(arrival)}, headers=auth_headers(student))
    steps = client.get("/me/steps", headers=auth_headers(student)).json()["steps"]
    expected = str(arrival + timedelta(days=7))
    assert steps[0]["due_date"] == expected


def test_due_date_days_before_visa_expiry(client, db):
    student = make_student(db, "visa@example.com")
    make_template(db, 1, DeadlineType.days_before_visa_expiry, deadline_days=30)

    visa = date(2026, 12, 31)
    client.put("/me/profile", json={
        "country_code": "KZ", "arrival_date": "2026-01-01", "visa_expiry": str(visa)
    }, headers=auth_headers(student))
    steps = client.get("/me/steps", headers=auth_headers(student)).json()["steps"]
    expected = str(visa - timedelta(days=30))
    assert steps[0]["due_date"] == expected


def test_due_date_none_when_visa_expiry_missing(client, db):
    """days_before_visa_expiry step has no due_date if visa_expiry not set."""
    student = make_student(db, "novisa@example.com")
    make_template(db, 1, DeadlineType.days_before_visa_expiry, deadline_days=30)

    client.put("/me/profile", json={"country_code": "KZ", "arrival_date": "2026-01-01"}, headers=auth_headers(student))
    steps = client.get("/me/steps", headers=auth_headers(student)).json()["steps"]
    assert steps[0]["due_date"] is None


# ── recalculation on date change ──────────────────────────────────────────────

def test_recalculate_due_date_on_arrival_change(client, db):
    student = make_student(db, "recalc@example.com")
    make_template(db, 1, DeadlineType.days_after_arrival, deadline_days=7)

    headers = auth_headers(student)
    client.put("/me/profile", json={"country_code": "KZ", "arrival_date": "2026-01-01"}, headers=headers)
    client.put("/me/profile", json={"country_code": "KZ", "arrival_date": "2026-02-01"}, headers=headers)

    steps = client.get("/me/steps", headers=auth_headers(student)).json()["steps"]
    expected = str(date(2026, 2, 1) + timedelta(days=7))
    assert steps[0]["due_date"] == expected


def test_approved_step_due_date_not_recalculated(client, db):
    """Approved steps keep their original due_date after profile update."""
    student = make_student(db, "approved@example.com")
    tmpl = make_template(db, 1, DeadlineType.days_after_arrival, deadline_days=7)

    headers = auth_headers(student)
    client.put("/me/profile", json={"country_code": "KZ", "arrival_date": "2026-01-01"}, headers=headers)

    # mark step as approved directly in DB
    step = db.query(StudentStep).filter(StudentStep.student_id == student.id).first()
    original_due = step.due_date
    step.status = StepStatus.approved
    db.flush()

    # change arrival date
    client.put("/me/profile", json={"country_code": "KZ", "arrival_date": "2026-06-01"}, headers=headers)

    db.refresh(step)
    assert step.due_date == original_due  # untouched


# ── isolation ────────────────────────────────────────────────────────────────

def test_student_sees_only_own_steps(client, db):
    student_a = make_student(db, "a@example.com")
    student_b = make_student(db, "b@example.com")
    make_template(db, 1, DeadlineType.none)

    client.put("/me/profile", json={"country_code": "KZ", "arrival_date": "2026-01-01"}, headers=auth_headers(student_a))
    client.put("/me/profile", json={"country_code": "KZ", "arrival_date": "2026-01-01"}, headers=auth_headers(student_b))

    r_a = client.get("/me/steps", headers=auth_headers(student_a)).json()
    r_b = client.get("/me/steps", headers=auth_headers(student_b)).json()

    # each student sees exactly 1 step
    assert r_a["total"] == 1
    assert r_b["total"] == 1
    # step IDs are different — each student got their own row
    id_a = r_a["steps"][0]["id"]
    id_b = r_b["steps"][0]["id"]
    assert id_a != id_b


# ── profile validation ────────────────────────────────────────────────────────

def test_country_code_lowercased_is_saved_as_upper(client, db):
    student = make_student(db, "lower@example.com")
    r = client.put("/me/profile", json={"country_code": "kz"}, headers=auth_headers(student))
    assert r.status_code == 200
    assert r.json()["country_code"] == "KZ"


def test_country_code_too_long_returns_422(client, db):
    student = make_student(db, "toolong@example.com")
    r = client.put("/me/profile", json={"country_code": "Kazakhstan"}, headers=auth_headers(student))
    assert r.status_code == 422


def test_course_out_of_range_returns_422(client, db):
    student = make_student(db, "course@example.com")
    r = client.put("/me/profile", json={"course": 7}, headers=auth_headers(student))
    assert r.status_code == 422


# ── load_steps validation ─────────────────────────────────────────────────────

def test_validate_step_data_passes_for_none_deadline():
    validate_step_data({"order": 1, "deadline_type": "none", "deadline_days": None}, 0)


def test_validate_step_data_passes_with_positive_days():
    validate_step_data({"order": 1, "deadline_type": "days_after_arrival", "deadline_days": 7}, 0)


def test_validate_step_data_fails_when_days_missing():
    with pytest.raises(ValueError, match="deadline_days"):
        validate_step_data({"order": 1, "title": "X", "deadline_type": "days_after_arrival", "deadline_days": None}, 0)


def test_validate_step_data_fails_when_days_zero():
    with pytest.raises(ValueError):
        validate_step_data({"order": 1, "title": "X", "deadline_type": "days_before_visa_expiry", "deadline_days": 0}, 0)
