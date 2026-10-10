from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.config import settings
from app.routers import chats, news, posts, users
from app.services.mcp.client import mcp_client
from app.services.tools import register_mcp_tools


@asynccontextmanager
async def lifespan(_: FastAPI):
    # ① 启动段:应用开始接请求之前,跑一次
    if settings.mcp_kb_server_cmd:
        tools = await mcp_client.start()
        register_mcp_tools(tools, mcp_client.call_tool)
    yield  # ② 应用在这里"活着",服务所有请求

    # ③ 关闭段:收到 Ctrl+C / SIGTERM 后,跑一次
    await mcp_client.stop()  # 杀掉子进程


app = FastAPI(title="Study Fastapi", lifespan=lifespan)
app.include_router(users.router)
app.include_router(posts.router)
app.include_router(news.router)
app.include_router(chats.router)


@app.get("/health")
def health():
    return {"status": "ok"}
