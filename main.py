from fastapi import FastAPI
from routers import students, tasks, auth

app = FastAPI()

app.include_router(students.router)
app.include_router(tasks.router)
app.include_router(auth.router)

@app.get("/")
def home():
    return {"message": "Привет, это бэкенд Migrant App"}

