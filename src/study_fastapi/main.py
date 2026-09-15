from fastapi import FastAPI

from study_fastapi import models  # type: ignore  # noqa: F401
from study_fastapi.database import Base, engine
from study_fastapi.routers import users

Base.metadata.create_all(bind=engine)


app = FastAPI(title="Study Fastapi")
app.include_router(users.router)


@app.get("/health")
def health():
    return {"status": "ok"}
