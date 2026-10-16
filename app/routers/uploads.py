import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import get_upload_dir
from app.db import get_db
from app.models.steps import StudentStep, StepStatus, StepTemplate
from app.models.user import User
from app.security import require_student

router = APIRouter(tags=["uploads"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

# Magic-byte signatures → file extension.
# We detect by file content, not filename or Content-Type header.
_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\x25\x50\x44\x46", ".pdf"),          # %PDF
    (b"\xff\xd8\xff", ".jpg"),               # JPEG
    (b"\x89\x50\x4e\x47\x0d\x0a\x1a\x0a", ".png"),  # PNG
]


def _detect_extension(data: bytes) -> str:
    """Return .pdf/.jpg/.png based on magic bytes; raise 415 otherwise."""
    for sig, ext in _SIGNATURES:
        if data[: len(sig)] == sig:
            return ext
    raise HTTPException(status_code=415, detail="Разрешены только PDF, JPG, PNG")


async def _read_limited(file: UploadFile) -> bytes:
    """Read UploadFile in 64 KB chunks; raise 413 as soon as size > MAX_UPLOAD_BYTES."""
    chunks: list[bytes] = []
    size = 0
    while True:
        chunk = await file.read(65_536)
        if not chunk:
            break
        size += len(chunk)
        if size > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Файл превышает 10 МБ")
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/me/steps/{step_id}/upload")
async def upload_file(
    step_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
    upload_dir: Path = Depends(get_upload_dir),
):
    # look up by id AND owner — never just by id alone
    step = (
        db.query(StudentStep)
        .filter(StudentStep.id == step_id, StudentStep.student_id == current_user.id)
        .first()
    )
    if not step:
        raise HTTPException(status_code=404, detail="Шаг не найден")

    template = db.get(StepTemplate, step.template_id)
    if not template.requires_upload:
        raise HTTPException(status_code=400, detail="Этот шаг не требует загрузки")

    if step.status == StepStatus.approved:
        raise HTTPException(status_code=409, detail="Шаг уже принят, загрузка невозможна")

    content = await _read_limited(file)
    ext = _detect_extension(content)

    # delete old file before saving the new one
    if step.file_path:
        old = upload_dir / step.file_path
        if old.exists():
            old.unlink()

    # filename is always a random UUID — original filename is completely ignored
    filename = f"{uuid.uuid4()}{ext}"
    (upload_dir / filename).write_bytes(content)

    step.file_path = filename           # relative path only
    step.status = StepStatus.submitted
    step.uploaded_at = datetime.utcnow()
    step.staff_comment = None           # clear previous rejection comment
    db.commit()

    return {"status": "submitted"}


@router.get("/me/steps/{step_id}/file")
def get_file(
    step_id: int,
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
    upload_dir: Path = Depends(get_upload_dir),
):
    step = (
        db.query(StudentStep)
        .filter(StudentStep.id == step_id, StudentStep.student_id == current_user.id)
        .first()
    )
    if not step:
        raise HTTPException(status_code=404, detail="Шаг не найден")
    if not step.file_path:
        raise HTTPException(status_code=404, detail="Файл не найден")

    full_path = upload_dir / step.file_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Файл не найден")

    return FileResponse(str(full_path))
