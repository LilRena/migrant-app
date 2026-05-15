from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import SessionLocal, Task, Student
from pydantic import BaseModel

app = FastAPI()
class TaskCreate(BaseModel):
    name: str
    deadline: str
    status: str

class TaskUpdate(BaseModel):
    name: str
    deadline: str
    status: str

def get_db():
    db=SessionLocal()
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

class StudentsUpdate(BaseModel):
    name: str
    country: str
    direction: str
    period: int
    visa_expiry: str
    registration_expiry: str

@app.get("/")
def home():
    return {"message": "Привет, это бэкенд Migrant App"}

@app.get("/tasks")
def get_tasks(db: Session = Depends(get_db)):
    tasks = db.query(Task).all()
    return tasks

@app.post("/tasks")
def create_tasks(task: TaskCreate, db: Session = Depends(get_db)):
    new_task = Task(name=task.name, deadline=task.deadline, status=task.status)
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task

@app.put("/tasks/{id}")
def update_tasks(id: int, task: TaskUpdate, db: Session = Depends(get_db)):
    task_db = db.query(Task).filter(Task.id == id).first()
    task_db.name = task.name
    task_db.status = task.status
    task_db.deadline = task.deadline
    db.commit()
    return task_db

@app.delete("/tasks/{id}")
def delete_tasks(id: int, db: Session = Depends(get_db)):
    task_db = db.query(Task).filter(Task.id == id).first()
    db.delete(task_db)
    db.commit()
    return {"message": "Задача удалена"}

@app.get("/students")
def get_students(db: Session = Depends(get_db)):
    students = db.query(Student).all()
    return students

@app.post("/students")
def post_students (students: StudentsCreate, db: Session = Depends(get_db)):
    new_student = Student(name=students.name, country=students.country, direction=students.direction, period=students.period, visa_expiry=students.visa_expiry, registration_expiry=students.registration_expiry )
    db.add(new_student)
    db.commit()
    db.refresh(new_student)
    return new_student

@app.put("/students/{id}")
def put_studdents (id: int, students: StudentsUpdate, db: Session = Depends(get_db)):
    students_db = db.query(Student).filter (Student.id == id ).first()
    students_db.name=students.name
    students_db.country=students.country
    students_db.direction=students.direction
    students_db.period=students.period
    students_db.visa_expiry=students.visa_expiry
    students_db.registration_expiry=students.registration_expiry
    db.commit()
    return students_db

@app.delete("/students/{id}")
def students_delete (id:int, db: Session = Depends(get_db)):
    students_db = db.query(Student).filter(Student.id == id).first()
    db.delete(students_db)
    db.commit()
    return {"message": "Студент удалён"}
