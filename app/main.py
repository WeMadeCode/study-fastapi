from fastapi import FastAPI

from app.routers import news, posts, users

app = FastAPI(title="Study Fastapi")
app.include_router(users.router)
app.include_router(posts.router)
app.include_router(news.router)


@app.get("/health")
def health():
    return {"status": "ok"}
