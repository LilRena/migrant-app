from fastapi import FastAPI

from app.routers import auth, staff, profile, steps, uploads

app = FastAPI(title="KFU Migrant")

app.include_router(auth.router)
app.include_router(staff.router)
app.include_router(profile.router)
app.include_router(steps.router)
app.include_router(uploads.router)


@app.get("/")
def health():
    return {"status": "ok"}
