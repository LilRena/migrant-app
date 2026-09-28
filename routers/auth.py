import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import Student
from auth import verify_password
from pydantic import BaseModel
from jose import jwt
from database import get_db

SECRET_KEY = os.getenv("SECRET_KEY", "смени-этот-ключ-в-продакшене")
ALGORITHM = "HS256"

class LoginData(BaseModel):
    email: str
    password: str

router = APIRouter()

def create_token(data: dict) -> str:
    return jwt.encode(data, SECRET_KEY, ALGORITHM)

@router.post("/login")
def login_students(login_data: LoginData, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.email == login_data.email).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Студент не найден")
    if not verify_password(login_data.password, student.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный пароль")
    return {"access_token": create_token({"sub": student.email}), "token_type": "bearer"}