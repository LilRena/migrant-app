from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import Task
from pydantic import BaseModel
from database import get_db
from dependencies import get_current_student
from database import Student

router = APIRouter()

class TaskCreate(BaseModel):
    name: str
    deadline: str
    status: str

class TaskUpdate(BaseModel):
    name: str
    deadline: str
    status: str

@router.get("/tasks")
def get_tasks(
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
):
    tasks = db.query(Task).all()
    return tasks

@router.post("/tasks")
def create_tasks(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
):
    new_task = Task(name=task.name, deadline=task.deadline, status=task.status)
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task

@router.put("/tasks/{id}")
def update_tasks(
    id: int,
    task: TaskUpdate,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
):
    task_db = db.query(Task).filter(Task.id == id).first()
    if not task_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
    task_db.name = task.name
    task_db.status = task.status
    task_db.deadline = task.deadline
    db.commit()
    return task_db

@router.delete("/tasks/{id}")
def delete_tasks(
    id: int,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
):
    task_db = db.query(Task).filter(Task.id == id).first()
    if not task_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
    db.delete(task_db)
    db.commit()
    return {"message": "Задача удалена"}