from fastapi import FastAPI

from study_fastapi.routers import posts, users

app = FastAPI(title="Study Fastapi")
app.include_router(users.router)
app.include_router(posts.router)


@app.get("/health")
def health():
    return {"status": "ok"}
