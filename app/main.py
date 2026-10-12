from fastapi import FastAPI

app = FastAPI(title="KFU Migrant")


@app.get("/")
def health():
    return {"status": "ok"}
