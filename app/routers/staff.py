from fastapi import APIRouter, Depends

from app.models.user import User
from app.security import require_staff

router = APIRouter(prefix="/staff", tags=["staff"])


@router.get("/students")
def list_students(current_user: User = Depends(require_staff)):
    # placeholder — full implementation in Stage 3
    return []
