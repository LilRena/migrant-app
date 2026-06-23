from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import Student, get_db
from pydantic import BaseModel
from auth import hash_password
from dependencies import get_current_student

router = APIRouter()

class StudentsCreate(BaseModel):
    name: str
    country: str
    direction: str
    period: int
    visa_expiry: str
    registration_expiry: str
    email: str
    hashed_password: str

class StudentsUpdate(BaseModel):
    name: str
    country: str
    direction: str
    period: int
    visa_expiry: str
    registration_expiry: str
    email: str

@router.post("/students")
def post_students(students: StudentsCreate, db: Session = Depends(get_db)):
    hashed = hash_password(students.hashed_password)
    new_student = Student(
        name=students.name,
        country=students.country,
        direction=students.direction,
        period=students.period,
        visa_expiry=students.visa_expiry,
        registration_expiry=students.registration_expiry,
        hashed_password=hashed,
        email=students.email
    )
    db.add(new_student)
    db.commit()
    db.refresh(new_student)
    return new_student

@router.get("/students/me")
def get_me(current_student: Student = Depends(get_current_student)):
    return current_student

@router.put("/students/me")
def update_me(
    students: StudentsUpdate,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    current_student.name = students.name
    current_student.country = students.country
    current_student.direction = students.direction
    current_student.period = students.period
    current_student.visa_expiry = students.visa_expiry
    current_student.registration_expiry = students.registration_expiry
    db.commit()
    return current_student

@router.delete("/students/me")
def delete_me(
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    db.delete(current_student)
    db.commit()
    return {"message": "Аккаунт удалён"}