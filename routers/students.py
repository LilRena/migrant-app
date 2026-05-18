from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import SessionLocal, Student
from pydantic import BaseModel
from auth import hash_password, verify_password

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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

@router.get("/students")
def get_students(db: Session = Depends(get_db)):
    students = db.query(Student).all()
    return students

@router.post("/students")
def post_students (students: StudentsCreate, db: Session = Depends(get_db)):
    hashed = hash_password(students.hashed_password)
    new_student = Student(name=students.name, country=students.country, direction=students.direction, period=students.period, visa_expiry=students.visa_expiry, registration_expiry=students.registration_expiry, hashed_password=hashed, email=students.email)
    db.add(new_student)
    db.commit()
    db.refresh(new_student)
    return new_student

@router.put("/students/{id}")
def put_students (id: int, students: StudentsUpdate, db: Session = Depends(get_db)):
    students_db = db.query(Student).filter (Student.id == id ).first()
    students_db.name=students.name
    students_db.country=students.country
    students_db.direction=students.direction
    students_db.period=students.period
    students_db.visa_expiry=students.visa_expiry
    students_db.registration_expiry=students.registration_expiry
    db.commit()
    return students_db

@router.delete("/students/{id}")
def students_delete (id:int, db: Session = Depends(get_db)):
    students_db = db.query(Student).filter(Student.id == id).first()
    db.delete(students_db)
    db.commit()
    return {"message": "Студент удалён"}