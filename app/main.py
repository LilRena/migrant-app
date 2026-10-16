from fastapi import FastAPI

from app.routers import auth, staff

app = FastAPI(title="KFU Migrant")

app.include_router(auth.router)
app.include_router(staff.router)


@app.get("/")
def health():
    return {"status": "ok"}
