"""Tests for Stage 3: file upload, download, staff review."""
import io
from datetime import datetime

from app.models.steps import StepTemplate, DeadlineType, StudentStep, StepStatus
from app.models.user import User, UserRole
from app.security import hash_password, create_token


# ── file content fixtures ─────────────────────────────────────────────────────

PDF_BYTES = b"%PDF-1.4 minimal"
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 16
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
ELF_BYTES = b"\x7fELF" + b"\x00" * 16          # Linux executable — not an image/pdf
OVERSIZED = b"%PDF" + b"\x00" * (10 * 1024 * 1024 + 1)  # 10 MB + 1 byte


# ── helpers ───────────────────────────────────────────────────────────────────

def make_student(db, email="student@example.com"):
    u = User(
        email=email,
        hashed_password=hash_password("password1"),
        full_name="Student",
        role=UserRole.student,
    )
    db.add(u)
    db.flush()
    return u


def make_staff(db, email="staff@example.com"):
    u = User(
        email=email,
        hashed_password=hash_password("staffpass1"),
        full_name="Staff",
        role=UserRole.staff,
    )
    db.add(u)
    db.flush()
    return u


def make_template(db, requires_upload=True):
    t = StepTemplate(
        country_code=None,
        order=1,
        title="Test step",
        deadline_type=DeadlineType.none,
        requires_upload=requires_upload,
        is_demo=True,
    )
    db.add(t)
    db.flush()
    return t


def make_step(db, student, template):
    s = StudentStep(student_id=student.id, template_id=template.id)
    db.add(s)
    db.flush()
    return s


def headers(user):
    return {"Authorization": f"Bearer {create_token({'sub': user.email})}"}


def upload(client, step_id, content, filename, user):
    return client.post(
        f"/me/steps/{step_id}/upload",
        files={"file": (filename, io.BytesIO(content), "application/octet-stream")},
        headers=headers(user),
    )


# ── upload: basic success cases ───────────────────────────────────────────────

def test_upload_pdf_succeeds(client, db):
    student = make_student(db)
    tmpl = make_template(db)
    step = make_step(db, student, tmpl)
    r = upload(client, step.id, PDF_BYTES, "doc.pdf", student)
    assert r.status_code == 200
    assert r.json()["status"] == "submitted"


def test_upload_jpeg_succeeds(client, db):
    student = make_student(db, "jpeg@example.com")
    tmpl = make_template(db)
    step = make_step(db, student, tmpl)
    r = upload(client, step.id, JPEG_BYTES, "photo.jpg", student)
    assert r.status_code == 200


def test_upload_png_succeeds(client, db):
    student = make_student(db, "png@example.com")
    tmpl = make_template(db)
    step = make_step(db, student, tmpl)
    r = upload(client, step.id, PNG_BYTES, "scan.png", student)
    assert r.status_code == 200


# ── upload: access control ────────────────────────────────────────────────────

def test_upload_to_another_students_step_returns_404(client, db):
    owner = make_student(db, "owner@example.com")
    other = make_student(db, "other@example.com")
    tmpl = make_template(db)
    step = make_step(db, owner, tmpl)

    r = upload(client, step.id, PDF_BYTES, "doc.pdf", other)
    assert r.status_code == 404


def test_download_another_students_file_returns_404(client, db):
    owner = make_student(db, "dlowner@example.com")
    other = make_student(db, "dlother@example.com")
    tmpl = make_template(db)
    step = make_step(db, owner, tmpl)
    upload(client, step.id, PDF_BYTES, "doc.pdf", owner)

    r = client.get(f"/me/steps/{step.id}/file", headers=headers(other))
    assert r.status_code == 404


# ── upload: file type detection ───────────────────────────────────────────────

def test_executable_renamed_pdf_is_rejected(client, db):
    """Type is detected by magic bytes, not filename."""
    student = make_student(db, "exe@example.com")
    tmpl = make_template(db)
    step = make_step(db, student, tmpl)
    r = upload(client, step.id, ELF_BYTES, "evil.pdf", student)
    assert r.status_code == 415


# ── upload: size limit ────────────────────────────────────────────────────────

def test_oversized_file_returns_413(client, db):
    student = make_student(db, "big@example.com")
    tmpl = make_template(db)
    step = make_step(db, student, tmpl)
    r = upload(client, step.id, OVERSIZED, "big.pdf", student)
    assert r.status_code == 413


# ── upload: path traversal ────────────────────────────────────────────────────

def test_path_traversal_filename_ignored(client, db, tmp_path):
    """A filename like ../../x.pdf must not affect where the file is saved."""
    student = make_student(db, "traversal@example.com")
    tmpl = make_template(db)
    step = make_step(db, student, tmpl)
    r = upload(client, step.id, PDF_BYTES, "../../evil.pdf", student)
    assert r.status_code == 200
    # the stored path must be a plain filename, no directory components
    db.refresh(step)
    assert "/" not in step.file_path
    assert "\\" not in step.file_path


# ── upload: approved step ─────────────────────────────────────────────────────

def test_upload_to_approved_step_returns_409(client, db):
    student = make_student(db, "approved@example.com")
    tmpl = make_template(db)
    step = make_step(db, student, tmpl)
    step.status = StepStatus.approved
    db.flush()

    r = upload(client, step.id, PDF_BYTES, "doc.pdf", student)
    assert r.status_code == 409


# ── role guard ────────────────────────────────────────────────────────────────

def test_staff_on_me_steps_returns_403(client, db):
    staff = make_staff(db)
    r = client.get("/me/steps", headers=headers(staff))
    assert r.status_code == 403


def test_student_on_staff_students_returns_403(client, db):
    student = make_student(db, "stustaff@example.com")
    r = client.get("/staff/students", headers=headers(student))
    assert r.status_code == 403


# ── staff: review ─────────────────────────────────────────────────────────────

def test_reject_without_comment_returns_422(client, db):
    staff = make_staff(db)
    student = make_student(db, "rej@example.com")
    tmpl = make_template(db)
    step = make_step(db, student, tmpl)
    step.status = StepStatus.submitted
    db.flush()

    r = client.post(
        f"/staff/steps/{step.id}/review",
        json={"decision": "reject", "comment": None},
        headers=headers(staff),
    )
    assert r.status_code == 422


def test_reject_with_empty_string_comment_returns_422(client, db):
    staff = make_staff(db, "staff2@example.com")
    student = make_student(db, "rej2@example.com")
    tmpl = make_template(db)
    step = make_step(db, student, tmpl)
    step.status = StepStatus.submitted
    db.flush()

    r = client.post(
        f"/staff/steps/{step.id}/review",
        json={"decision": "reject", "comment": "   "},
        headers=headers(staff),
    )
    assert r.status_code == 422


def test_review_non_submitted_step_returns_409(client, db):
    staff = make_staff(db, "staff3@example.com")
    student = make_student(db, "todo@example.com")
    tmpl = make_template(db)
    step = make_step(db, student, tmpl)  # default status = todo

    r = client.post(
        f"/staff/steps/{step.id}/review",
        json={"decision": "approve"},
        headers=headers(staff),
    )
    assert r.status_code == 409


# ── full cycle ────────────────────────────────────────────────────────────────

def test_full_cycle(client, db):
    """Upload → reject with comment → student sees comment → re-upload → approve → done++."""
    staff = make_staff(db, "cycle_staff@example.com")
    student = make_student(db, "cycle_student@example.com")
    tmpl = make_template(db)
    step = make_step(db, student, tmpl)

    # 1. student uploads
    r = upload(client, step.id, PDF_BYTES, "doc.pdf", student)
    assert r.status_code == 200

    # 2. staff rejects with comment
    r = client.post(
        f"/staff/steps/{step.id}/review",
        json={"decision": "reject", "comment": "Плохое качество"},
        headers=headers(staff),
    )
    assert r.status_code == 200

    # 3. student sees the comment in their steps
    r = client.get("/me/steps", headers=headers(student))
    assert r.status_code == 200
    step_data = next(s for s in r.json()["steps"] if s["id"] == step.id)
    assert step_data["status"] == "rejected"
    assert step_data["staff_comment"] == "Плохое качество"
    assert r.json()["done"] == 0

    # 4. student re-uploads (old file must be deleted from disk)
    first_file = step_data  # we just need to know there's a file
    db.refresh(step)
    old_filename = step.file_path

    r = upload(client, step.id, PDF_BYTES, "doc2.pdf", student)
    assert r.status_code == 200
    db.refresh(step)
    assert step.file_path != old_filename  # new UUID filename
    assert step.staff_comment is None       # comment cleared

    # 5. staff approves
    r = client.post(
        f"/staff/steps/{step.id}/review",
        json={"decision": "approve"},
        headers=headers(staff),
    )
    assert r.status_code == 200

    # 6. done count increased
    r = client.get("/me/steps", headers=headers(student))
    assert r.json()["done"] == 1
