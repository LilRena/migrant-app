from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import SessionLocal, Student
from auth import verify_password
from pydantic import BaseModel
from jose import jwt
from database import get_db

SECRET_KEY = "твой_секретный_ключ"
ALGORITHM = "HS256"

class LoginData(BaseModel):
    email: str
    password: str

router = APIRouter()

def create_token(data: dict) -> str:
    return jwt.encode(data,SECRET_KEY,ALGORITHM)

@router.post("/login")
def login_students (login_data: LoginData, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.email == login_data.email).first()
    if not student:
        return {"error": "Студент не найден"}
    if not verify_password(login_data.password, student.hashed_password):
        return {"error": "Неверный пароль"}
    return create_token ({"sub": student.email})