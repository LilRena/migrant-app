from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import SessionLocal, Task
from pydantic import BaseModel

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class TaskCreate(BaseModel):
    name: str
    deadline: str
    status: str

class TaskUpdate(BaseModel):
    name: str
    deadline: str
    status: str

@router.get("/tasks")
def get_tasks(db: Session = Depends(get_db)):
    tasks = db.query(Task).all()
    return tasks

@router.post("/tasks")
def create_tasks(task: TaskCreate, db: Session = Depends(get_db)):
    new_task = Task(name=task.name, deadline=task.deadline, status=task.status)
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task

@router.put("/tasks/{id}")
def update_tasks(id: int, task: TaskUpdate, db: Session = Depends(get_db)):
    task_db = db.query(Task).filter(Task.id == id).first()
    task_db.name = task.name
    task_db.status = task.status
    task_db.deadline = task.deadline
    db.commit()
    return task_db

@router.delete("/tasks/{id}")
def delete_tasks(id: int, db: Session = Depends(get_db)):
    task_db = db.query(Task).filter(Task.id == id).first()
    db.delete(task_db)
    db.commit()
    return {"message": "Задача удалена"}