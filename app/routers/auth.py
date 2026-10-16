from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.user import User, UserRole
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from app.security import hash_password, verify_password, create_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

# same message for wrong email and wrong password — prevents email enumeration
_BAD_CREDENTIALS = "Неверный email или пароль"


@router.post("/register", response_model=UserResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=UserRole.student,  # registration is always student
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    # check both existence and password before raising — same error either way
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_BAD_CREDENTIALS)
    token = create_token({"sub": user.email})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user
